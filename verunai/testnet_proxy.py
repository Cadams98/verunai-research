"""Loopback TCP relay that counts the bytes exchanged with one testnet node.

The harness gives each node a relay and lists the *relay* addresses as peers, so
every node-to-node HTTP exchange passes through a relay. The counts are
application-layer bytes (HTTP headers and bodies); TCP/IP overhead is excluded.
Harness monitoring traffic goes directly to nodes and is not counted.

The relay only forwards bytes. It never parses, alters, delays, or drops data,
so node behaviour and consensus are unchanged. It binds to 127.0.0.1 only.
"""

from __future__ import annotations

import socket
import threading

LOOPBACK = "127.0.0.1"
_CHUNK = 65_536


class CountingRelay:
    """Forward loopback TCP connections to one node and count bytes in each direction.

    Attributes:
        target_port: Port of the node that receives forwarded connections.
        idle_timeout: Seconds a connection may stay silent before it is closed.
    """

    def __init__(self, target_port: int, idle_timeout: float = 15.0) -> None:
        if not 1 <= target_port <= 65535:
            raise ValueError("target_port must be 1..65535")
        if not 0.5 <= idle_timeout <= 120:
            raise ValueError("idle_timeout must be 0.5..120 seconds")
        self.target_port = target_port
        self.idle_timeout = idle_timeout
        self._lock = threading.Lock()
        self._counts = {"bytes_to_node": 0, "bytes_from_node": 0, "connections": 0,
                        "upstream_failures": 0}
        self._listener: socket.socket | None = None
        self._threads: list[threading.Thread] = []
        self._open: set[socket.socket] = set()
        self._stopping = threading.Event()

    def start(self) -> int:
        """Bind an ephemeral loopback port, begin accepting, and return the port."""
        if self._listener is not None:
            raise RuntimeError("Relay already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind((LOOPBACK, 0))
        listener.listen(64)
        listener.settimeout(0.2)
        self._listener = listener
        thread = threading.Thread(target=self._accept_loop, name="relay-accept", daemon=True)
        thread.start()
        self._threads.append(thread)
        return int(listener.getsockname()[1])

    def counts(self) -> dict:
        """Return a snapshot of the byte and connection counters."""
        with self._lock:
            return dict(self._counts)

    def stop(self) -> None:
        """Close the listener and every open connection, then join worker threads."""
        self._stopping.set()
        if self._listener is not None:
            self._listener.close()
        with self._lock:
            sockets = list(self._open)
        for sock in sockets:
            _close_quietly(sock)
        for thread in list(self._threads):
            thread.join(timeout=2.0)

    def _accept_loop(self) -> None:
        assert self._listener is not None
        while not self._stopping.is_set():
            try:
                client, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            thread = threading.Thread(target=self._serve, args=(client,), name="relay-conn",
                                      daemon=True)
            thread.start()
            self._threads.append(thread)

    def _serve(self, client: socket.socket) -> None:
        try:
            upstream = socket.create_connection((LOOPBACK, self.target_port),
                                                timeout=self.idle_timeout)
        except OSError:
            with self._lock:
                self._counts["upstream_failures"] += 1
            _close_quietly(client)
            return
        client.settimeout(self.idle_timeout)
        with self._lock:
            self._counts["connections"] += 1
            self._open.update((client, upstream))
        back = threading.Thread(target=self._pump, args=(upstream, client, "bytes_from_node"),
                                name="relay-pump", daemon=True)
        back.start()
        self._pump(client, upstream, "bytes_to_node")
        back.join(timeout=self.idle_timeout + 1)
        for sock in (client, upstream):
            _close_quietly(sock)
            with self._lock:
                self._open.discard(sock)

    def _pump(self, source: socket.socket, destination: socket.socket, counter: str) -> None:
        try:
            while True:
                data = source.recv(_CHUNK)
                if not data:
                    break
                destination.sendall(data)
                with self._lock:
                    self._counts[counter] += len(data)
        except OSError:
            pass
        finally:
            # Propagate end-of-stream so the other direction can finish cleanly.
            try:
                destination.shutdown(socket.SHUT_WR)
            except OSError:
                pass


def _close_quietly(sock: socket.socket) -> None:
    try:
        sock.close()
    except OSError:
        pass
