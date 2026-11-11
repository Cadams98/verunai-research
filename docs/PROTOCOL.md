# Protocol sketch (v0.1 toy research implementation)

## Goal
A miner attempts a nonce-dependent task used to update a shared next-token model; if their block hash meets the target they may append one block and receive fixed issuance. All nodes replay accepted blocks to reconstruct identical model state and balances.

## Canonical fields
`version, height, prev_hash, miner, nonce, difficulty, reward, updates`; `hash = SHA256(canonical_json(fields))` with sorted keys and compact delimiters. SHA-256 threshold uses `difficulty` leading zero hexadecimal digits. Genesis head = 64 zero hex digits. A single fixed chain difficulty applies to all demo blocks.

## Toy useful computation
A fixed original English training string supplies `(character, next_character)` pairs. For a candidate, SHA-256 of `(prev_hash, miner, nonce)` selects a repeatable strided batch of 48 training pairs. The miner produces a sorted sparse integer count update to a shared character-level bigram language model. Validators recompute exactly that one batch to verify the update. The winning update increases global counts; a smoothed next-character model produces measurable decreasing loss on training data as blocks accumulate.

## Why this is not trustless AI proof-of-work yet
- Training counts are cheap and can potentially be bypassed with mathematical shortcuts.
- There are no guarantees that all competitive compute was useful, nor that all useful work survives.
- Verification-to-generation ratio is good only due to repeated lottery attempts, **not** because useful AI model training is intrinsically easy to verify.
- An adversary might exploit public data, precompute batches, or use algorithms that produce hashes faster than honest model training.
- A random miner ID is not a wallet key; this demo has no cryptographic ownership, authenticated peers, fork choice, or economic security.
- Model quality measures training-set fit only; it can overfit, and it is not a general-purpose generative AI.
- GPU performance is not modeled by the simulator's relative attempt weights.

## Research questions for v0.2
1. What *genuinely valuable AI training or inference* unit can be committed to an unpredictable fresh challenge?
2. What is the quantitative cost of verifying one unit relative to producing candidates? Does a GPU actually help?
3. Could a miner find a valid commitment without computing the expensive AI task?
4. Can an adversary submit malicious model updates that verify syntactically but ruin model usefulness?
5. How do we let losing miners' work benefit the AI, without paying for spam or double-counting?
6. How do independent nodes agree during network delays, forks, and software/hardware numerical differences?
7. How do we preserve training privacy and prevent IP/data leakage?

## Production-path alternatives to evaluate
- Proof-of-work block security + separately metered/verifiable AI compute rewards (safer architecture, less philosophically pure).
- GPU-verifiable training/inference via cryptographic proofs or probabilistic audits (research risk).
- Reward useful AI work with audited service credits while keeping chain consensus separate.

No alternative is considered solved. Assess against security, usefulness, latency, hardware fairness, and economics.

## v0.4 networking extension — research only

`python -m verunai node` starts one independently executing miner/validator with a thread-safe chain state. `GET /status` advertises the research-only network identifier, chain height, hash, and fixed difficulty. Nodes with explicitly configured HTTP peer URLs can relay validated `POST /block` proposals and fetch `GET /chain` for replay-verified synchronization.

**Demo fork choice:** compare verified chains by `(block_count, -hex_to_int(tip_hash))`. This chooses the longer valid chain and uses the smaller tip hash on equal heights. It is intentionally simplistic and **does not** establish a production security property. Both nodes may temporarily create competing blocks; only blocks in the selected surviving chain earn fictional rewards.

**Persistence:** each accepted/adopted chain is written to a JSON file and fully replayed before restart. No funds can be transferred and a miner label is not a secure identity. There is no peer authentication or encryption.

**Versioning:** block serialization and hashing still use protocol version 1. Network compatibility is announced by a plain HTTP marker but is not cryptographically bound to consensus data. Any future security protocol must use explicit domain separation and versioned genesis parameters. See `PRIVATE_TESTNET.md` and `ATTACK_SURFACE.md`.

**Separate GPU research:** the optional `gpu-benchmark` command trains a small PyTorch neural model with gradients and is **not** used as consensus input. Cross-device deterministic validation is an unsolved task and must be addressed before proof-of-useful-work claims.
