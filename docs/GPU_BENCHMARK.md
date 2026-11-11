# Real neural training CPU/CUDA benchmark (optional)

This benchmark does actual PyTorch neural-network gradient training; **it is not hooked into consensus or blockchain block rewards**.

## Set up on your NVIDIA Windows desktop

1. Install Python 3.10+ and check `python --version` in PowerShell.
2. Install the appropriate PyTorch build for your NVIDIA driver/CUDA support using the **official selector** at <https://pytorch.org/get-started/locally/>. The CPU-only build will work but will not exercise your GPU.
3. Open PowerShell in this project folder and execute:

```powershell
python -m verunai gpu-benchmark --device auto --steps 50 --width 256 --batch 128
```

`--device cuda` errors if a working NVIDIA/CUDA PyTorch environment is not detected. `--device cpu` forces an independent CPU baseline. Report these two separate runs, including PyTorch version, device name, elapsed seconds, and loss changes.

## What it computes

A small two-layer feed-forward network learns a fixed synthetic teacher mapping with AdamW optimization. It measures training steps per second and mean-squared training loss on a fixed batch. This is **real neural training** but does not represent language-model quality or useful public knowledge acquisition.

## Known limits

- CUDA may run asynchronously; this benchmark synchronizes before and after timing.
- Fixed random seeds are not enough for consensus-safe reproducibility on all hardware.
- The speed metric is on synthetic workloads; do not extrapolate to profitable mining.
- Higher training speed does not necessarily mean a miner will win more blocks in the current CPU-only proof-of-work implementation.
- Record electrical power consumption separately if estimating operating economics.
