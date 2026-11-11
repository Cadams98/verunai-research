"""Opt-in neural-network *training benchmark* for AI-compute research.

This is not consensus logic. Do not use floating point GPU results directly for
block validity: different hardware can produce slightly different answers.
"""
from __future__ import annotations

from time import perf_counter


def neural_benchmark(steps: int = 30, width: int = 128, batch: int = 64,
                     device: str = "auto") -> dict:
    if not 2 <= steps <= 1000 or not 16 <= width <= 2048 or not 8 <= batch <= 4096:
        raise ValueError("steps=2..1000, width=16..2048, batch=8..4096")
    if device not in ("auto", "cpu", "cuda"):
        raise ValueError("device must be auto, cpu or cuda")
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch not installed. Follow docs/GPU_BENCHMARK.md") from exc
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA not available in this PyTorch installation")
    selected = "cuda" if device == "auto" and torch.cuda.is_available() else "cpu" if device == "auto" else device
    torch.manual_seed(314159)
    if selected == "cuda":
        torch.cuda.manual_seed_all(314159)
    x = torch.randn(batch, width, device="cpu").to(selected)
    teacher = torch.randn(width, width, device="cpu").to(selected) / width ** 0.5
    target = x @ teacher
    model = torch.nn.Sequential(
        torch.nn.Linear(width, width // 2),
        torch.nn.GELU(),
        torch.nn.Linear(width // 2, width),
    ).to(selected)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.007)

    def synchronize() -> None:
        if selected == "cuda":
            torch.cuda.synchronize()

    with torch.no_grad():
        initial_loss = float(torch.nn.functional.mse_loss(model(x), target).item())
    synchronize()
    start = perf_counter()
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        prediction = model(x)
        loss = torch.nn.functional.mse_loss(prediction, target)
        loss.backward()
        optimizer.step()
    synchronize()
    elapsed = perf_counter() - start
    with torch.no_grad():
        final_loss = float(torch.nn.functional.mse_loss(model(x), target).item())
    return {
        "framework": f"PyTorch {torch.__version__}",
        "device": selected,
        "gpu_name": torch.cuda.get_device_name(0) if selected == "cuda" else None,
        "steps": steps,
        "network_width": width,
        "batch_size": batch,
        "elapsed_seconds": round(elapsed, 4),
        "training_steps_per_second": round(steps / max(elapsed, 1e-9), 2),
        "loss_before": round(initial_loss, 6),
        "loss_after": round(final_loss, 6),
        "improved_on_training_data": final_loss < initial_loss,
        "note": "Real neural training benchmark only. NOT consensus, verifiable PoUW, or mining rewards. CPU/CUDA numerical differences can break consensus.",
    }
