# Verunai research milestone v0.5 — neural training bound to mined blocks

## Outcome

A separately versioned experimental blockchain (`neural-v2`) now runs deterministic neural linear-layer training during candidate generation and independent peer validation. The training update is consensus critical: forging the gradient digest, model digest, miner, or nonce invalidates the candidate. Localhost mining nodes run in separate operating-system processes and agree on chain history and resulting model state.

**Important limitation:** selection still uses SHA-256 and verification repeats the entire update. This is NOT secure Proof of Useful Work, a generalized language model, or a public cryptocurrency.

## Commands that reproduce the milestone

```bash
python -m unittest discover -s tests -v
python -m verunai mine --protocol neural-v2 --difficulty 1 --blocks 4 --powers 1,2 --output neural-chain.json
python -m verunai audit neural-chain.json
python -m verunai demo-testnet --protocol neural-v2 --blocks 5 --difficulty 1
python -m verunai neural-mining-benchmark --attempts 150
```

The standalone training benchmark from the previous release is still available:

```bash
python -m verunai gpu-benchmark --device auto --steps 30
```

## Recorded run in this environment (November 10, 2026)

- Two independently launched local processes completed five valid neural-v2 blocks, agreed on the same final block hash, and reconstructed the same model state. One run credited 150 fictional TEST units to `bob` and 100 to `alice`.
- The model's in-sample mean squared error decreased from `36.000000` to `35.804858` in that five-block run; this is a toy dataset, not a language understanding benchmark, and not every block necessarily reduces error.
- The 150-candidate CPU benchmark processed approximately **469 neural candidates/second**, with **2.15 ms median full-block validation** on this runtime. These are not consumer-GPU results and not production-level throughput.
- All **30 test cases** executed; 29 passed and one CUDA-only parity test was skipped because this environment has no CUDA GPU. PyTorch CPU parity tests passed. Exact evidence is under `evidence/`.

## Correctness and audit coverage

The v0.5 suite adds explicit tests for reproducible gradients, independent Python-vs-PyTorch arithmetic, training-data error evaluation, forged gradient and state commitments, changed miner or nonce, fake rewards, cross-version replay, peer relay, persistent replay, mismatched peer modes, and separate-process neural-v2 synchronization. CUDA parity is tested only when an NVIDIA/CUDA-capable runner is present.

## Security / scientific interpretation

There is no reason to believe an attacker must pay the intended neural training cost for every valid proposal. That property requires independent research, and a cheap, verifiable useful-work proof remains an open task. A stronger accelerator may generate more candidates per second, but measuring it requires real hardware and a secure task definition. Full-corpus error on the included sample is a toy, in-sample metric. Improving it does not demonstrate useful language understanding.

## Next engineering priorities

1. Batched GPU candidates and CPU reference validation on an RTX 5070; measure speed and energy per **accepted block**, not synthetic FLOPS alone.
2. Test shortcuts and gradient caching, including adversarial attempts to win without doing valid training.
3. Explore how **losing miners' outputs** could improve a shared model without allowing spam, model contamination, or reward fraud.
4. Develop safer independent-node transport and actual cryptographic miner identities, while keeping reward balances fictional until audited.
5. Bring external cryptography and machine-learning reviewers into a public code review before promoting any token economics.
