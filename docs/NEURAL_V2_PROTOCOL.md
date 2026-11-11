# VERUNAI neural-v2 protocol — experimental, not production consensus

**Research version:** 0.5 | **Block protocol:** 2 | **Network ID:** `verunai-private-neural-experiment-v2`.

## Why this exists

Version 1 included a deterministic character-count update attached to conventional hash mining. V2 tests whether a *real neural gradient* can be included as a consensus-critical step rather than remaining a separate benchmark. Its task is a small trainable **integer-quantized linear neural layer**, not a large language model.

## What miners actually compute

1. The current verified chain defines a `16×16` integer weight matrix `W`, initially all zeros.
2. A fresh parent block hash, miner ID, and nonce select a deterministic batch of 64 text examples from a fixed public corpus. Each input becomes a **16-dimensional dense signed context embedding**, and each target is a coarse next-character class.
3. The miner computes predictions `P = X · W`, errors `E = P − Y`, and a gradient `G = Xᵀ · E`.
4. The miner computes an integer weight update `W' = W − trunc_toward_zero(G / 192)`. All arithmetic is fully specified and reproducible.
5. The candidate block commits to `SHA256(G)`, `SHA256(W')`, the previous hash, its nonce, its miner name, and a domain separator.
6. A SHA-256 lottery determines eligibility (specified by demo difficulty). **This hash lottery is still the final winner selection mechanism.**
7. Independent validators **recompute the entire gradient and update**, compare both commitments, recompute the block hash, check difficulty, and only then award 50 fictional TEST units and incorporate `W'`.
8. Fork changes revert the model to the replayed canonical chain state. Old v1 chains cannot be interpreted as v2 chains.

This trains a small mathematical prediction model in an actual supervised gradient-descent step. Whether that step measurably improves model error depends on the sampled data and quantization; **lower training error is not guaranteed for every block**, and in-sample error is not real language ability.

## Determinism and GPU experiment

The canonical verifier uses only Python integers. An optional PyTorch compute backend implements the two dense multiplications in float64, which can exactly represent the bounded integers in this research configuration. A candidate is only valid if the resulting integer gradient and model digest match the canonical implementation. GPU acceleration has **not** been measured or verified on the user's hardware; float64 may be inefficient on consumer graphics cards. A larger batched workload and carefully proven arithmetic bounds are future research steps.

`python -m verunai mine --protocol neural-v2 --difficulty 1 --blocks 5 --powers 1,2`

`python -m verunai demo-testnet --protocol neural-v2 --difficulty 1 --blocks 5`

`python -m verunai neural-mining-benchmark --attempts 150 --backend python`

## Security failures and unresolved questions

- **Not proven useful Proof of Work:** a cheap mathematical method, preprocessing, alternative commitment search, or task-specific exploit might avoid honest neural computation. Merely checking a gradient is not a general cryptographic proof of the miner's cost.
- **No verification speedup:** verifying a winning block involves essentially the same computation as creating one candidate. Bitcoin's cheap hash verification is not matched for a large model.
- **Nonce grinding / model bias:** miners choose nonces and influence which minibatches are accepted. This can bias learning even if all computations are correct.
- **Wasted losing work:** computation from nonwinning candidates does not train the shared model.
- **No neural-model generality:** this is a tiny supervised linear predictor over a toy dataset, not distributed training of a chatbot.
- **Weak identity/networking:** miner IDs are user-provided strings; peer messages use unauthenticated localhost HTTP. Rewards cannot be owned or transferred securely.
- **No production economics or public-network consensus:** fixed difficulty and issuance, simple fork selection, no signed wallets or cryptographic finality.
- **Time-to-verify scales linearly with work:** as tasks become larger, verifier load can create denial-of-service vulnerabilities.

**Required next research:** robust consensus-coupled useful computation, succinct verification or fraud proofs, bounded adversarial validation costs, model poisoning defenses, batched GPU research, and independent cryptographic review.
