"""Read CPU time and peak memory of local child processes using only the standard library.

The testnet harness uses these readings as *observations*, not benchmarks. Each
function returns ``None`` values with a reason when the platform does not offer
a reliable source, rather than estimating.

Supported sources:
    * Windows: ``GetProcessTimes`` and ``K32GetProcessMemoryInfo`` via ``ctypes``.
    * Linux: ``/proc/<pid>/stat`` (user + system ticks) and ``/proc/<pid>/status``
      (``VmHWM``, the peak resident set size).
Other platforms report the metrics as unavailable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_WINDOWS_STILL_ACTIVE = 259
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PROCESS_VM_READ = 0x0010


def launcher_warning() -> str | None:
    """Explain why child-process metrics may describe a launcher, not the node.

    On Windows a virtual environment's ``python.exe`` is a small redirector that
    starts the base interpreter as a *second* process. Metrics for the PID that
    ``subprocess`` returns would then describe the redirector.

    Returns:
        A human-readable warning, or ``None`` when the PID is the interpreter itself.
    """
    if os.name == "nt" and sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return "Windows virtual-environment launcher detected; per-node metrics would describe the launcher"
    return None


def pid_alive(pid: int) -> bool:
    """Return whether a process with this PID is still running.

    Args:
        pid: Operating-system process identifier.

    Returns:
        ``True`` if the process exists and has not exited.
    """
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == _WINDOWS_STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    status = Path(f"/proc/{pid}/status")
    if status.exists():
        # A zombie (exited, not yet reaped) is not running.
        for line in status.read_text(encoding="ascii", errors="replace").splitlines():
            if line.startswith("State:"):
                return "Z" not in line.split(":", 1)[1]
    return True


def sample_process(pid: int) -> dict:
    """Read cumulative CPU seconds and peak resident memory for a running process.

    Args:
        pid: Operating-system process identifier of a live process.

    Returns:
        ``{"cpu_seconds": float | None, "peak_rss_bytes": int | None,
        "source": str, "unavailable_reason": str | None}``.
    """
    warning = launcher_warning()
    if warning:
        return _unavailable(warning)
    try:
        if os.name == "nt":
            return _sample_windows(pid)
        if Path(f"/proc/{pid}/stat").exists():
            return _sample_linux(pid)
    except (OSError, ValueError) as error:
        return _unavailable(f"Measurement failed: {type(error).__name__}")
    return _unavailable("No supported process-metrics source on this platform")


def _unavailable(reason: str) -> dict:
    return {"cpu_seconds": None, "peak_rss_bytes": None, "source": "unavailable",
            "unavailable_reason": reason}


def _sample_linux(pid: int) -> dict:
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    # The command name (field 2) may contain spaces, so split after its closing parenthesis.
    fields = stat[stat.rindex(")") + 2:].split()
    ticks = int(fields[11]) + int(fields[12])  # utime + stime (fields 14 and 15 overall)
    cpu_seconds = ticks / os.sysconf("SC_CLK_TCK")
    peak_kib = None
    for line in Path(f"/proc/{pid}/status").read_text(encoding="ascii").splitlines():
        if line.startswith("VmHWM:"):
            peak_kib = int(line.split()[1])
    return {"cpu_seconds": round(cpu_seconds, 4),
            "peak_rss_bytes": None if peak_kib is None else peak_kib * 1024,
            "source": "linux-proc", "unavailable_reason": None}


def _sample_windows(pid: int) -> dict:
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION | _PROCESS_VM_READ, False, pid)
    if not handle:
        raise OSError("OpenProcess failed")
    try:
        creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time),
                                        ctypes.byref(kernel), ctypes.byref(user)):
            raise OSError("GetProcessTimes failed")
        to_ticks = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime  # 100 ns units
        cpu_seconds = (to_ticks(kernel) + to_ticks(user)) / 10_000_000
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not kernel32.K32GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise OSError("K32GetProcessMemoryInfo failed")
        return {"cpu_seconds": round(cpu_seconds, 4),
                "peak_rss_bytes": int(counters.PeakWorkingSetSize),
                "source": "windows-kernel32", "unavailable_reason": None}
    finally:
        kernel32.CloseHandle(handle)
