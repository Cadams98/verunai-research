# Verunai v0.4 — First independent-node testnet milestone

**Working name:** Verunai. **Mission:** Built by everyone. Verified by anyone.

## Demonstrated and independently rechecked

- Two separate Python operating-system processes run independent miners/validators over actual localhost HTTP.
- Blocks compete against a SHA-256 toy target and commit to deterministic character-transition updates.
- Accepted blocks propagate between peers; nodes pull, independently verify, and adopt valid forked chains under a deterministic experimental rule.
- Each node may persist, restart, and replay its own chain.
- A built-in command launches two miner processes and verifies **both** saved chains agree: `python -m verunai demo-testnet --blocks 8 --difficulty 2`.
- An automated suite of **17 tests passed** in this development environment, including tampered-chain rejection, late joining, fork choice, serialization checks, oversize HTTP rejection, and two-process convergence.
- A separate optional PyTorch benchmark runs real neural-network gradient descent, reports CPU/GPU device, speed, and training loss. This environment confirmed CPU training; the NVIDIA RTX 5070 path is **not yet tested**.

## Evidence

- `evidence/two_node_local_run.json`: independently executed two-node testnet demonstration with converged chain and imaginary reward balances.
- `evidence/real_neural_cpu_run.json`: measured CPU training benchmark, where training loss decreased.
- `evidence/test_results.txt`: recorded 17 passing automated tests.

## Most important remaining blocker

A valid v1 block does **not** prove a miner performed costly useful AI training. This is presently a SHA-256 puzzle with a toy AI update inside each candidate. Both creating and verifying updates are trivial and may be shortcut. Neither the local testnet nor the GPU benchmark proves we have invented trustless proof of useful AI work.

## Next milestone

Design and adversarially benchmark a genuinely useful, hard-to-fake AI computational unit whose verification is inexpensive and reliable across heterogeneous hardware. Separately add authenticated peers, proper cumulative-work fork choice, resource bounds, network/genesis binding, and a cryptographically signed identity model. Keep test rewards imaginary and do not issue a real token or invite paid miners yet.

## Quick start

**Windows:** double click `START_WINDOWS.bat` if Python 3.10+ is installed, or open PowerShell and execute:

```
python -m verunai demo-testnet --blocks 8 --difficulty 2
python -m unittest discover -s tests -v
```

To benchmark real training on your own NVIDIA GPU, install a suitable CUDA-capable PyTorch build per `docs/GPU_BENCHMARK.md`, then execute:

```
python -m verunai gpu-benchmark --device cuda --steps 50 --width 256 --batch 128
```

See `docs/PRIVATE_TESTNET.md` for independent manual nodes. Avoid public Internet exposure.
