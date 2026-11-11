# Threat model and known breaks — READ BEFORE SHARING

## Critical: Useful AI work cannot yet secure the chain

1. **Training bypass / work laundering (critical).** Mining currently chooses a tiny, deterministic text-transition update from public source text, then computes a SHA-256 hash. The update is trivially reproducible and may be cached or optimized away. No proof links real neural training cost to block eligibility. A faster hash-oriented strategy can dominate without advancing useful AI research.
2. **Only winning work contributes (critical for purpose).** Work done by miners that lose the block race is discarded. This is a substantial waste and not the desired collective training system.
3. **Rewards are forgeable as identities (critical for money).** `miner` is only a string; it is not a public-key account. An attacker can use anybody's display name. No actual financial value can be protected here.
4. **Open HTTP peer endpoints (critical for public deployment).** Peers have no transport encryption or authentication, and user-supplied peer URLs cause outbound HTTP requests. Bind to loopback only by default. The `--allow-lan` switch does not add safety.
5. **Naive fork choice (critical for security).** Fixed-difficulty longest validated chain with a low-hash tie break is merely a local demonstration; peers can race, fork, and replace model state. There are no finality, confirmation, or accumulated-work guarantees.
6. **Static corpus / model poisoning (high).** The text and model code are fixed inside the interpreter. A production network needs authenticated, licensed, and auditable datasets, and explicit safe model-update selection.
7. **Unbounded adversarial incentives (high).** Fixed 50 TEST reward with no issuance cap, fees, difficulty adjustment, hashpower analysis, or cost model. No evidence tokens would have value.
8. **Replay and resource exhaustion (high).** Every `/chain` response is a full JSON ledger, verified from genesis. Limits are present but cannot prevent CPU starvation or all adversarial flooding; HTTP request threads are unbounded.
9. **GPU nondeterminism (high).** Floating-point neural-network training may produce different outputs across devices, driver versions, or kernels; do not use such results in block validation without a rigorously specified deterministic proof.
10. **Cross-network confusion (medium).** The network identifier is an HTTP handshake convention, not committed to the block header. In a financial system a network/genesis identifier must be cryptographically bound into every proof and transaction.

## Research attack tests already included

- Tampering with a model update is rejected.
- Increasing an issuance reward breaks replay validation.
- Tampered peer chain is rejected without changing the local ledger.
- Differing forks are replayed and resolved by a deterministic demonstration rule.
- Oversized or malformed incoming block HTTP payloads are rejected.
- Saved chains are replay-verified before a node resumes mining.
- Two actual OS processes synchronize on one reconstructed chain.

These do not substitute for external security review.

## Next proof-of-useful-work research questions

1. Define a computational unit useful to a **shared model** whose computation cannot profitably be skipped, faked, or efficiently precomputed.
2. Create a challenger who tries to win a block without doing that unit. Measure any advantage versus honest GPU mining.
3. Define verification cost per successful proof and per rejected proof. Test adversarial workloads.
4. Specify how losing miners' verified updates can improve the shared model without enabling cheap spam/poisoning.
5. Identify trust assumptions that remain in data selection, model checkpoints, and networking; get independent cryptography review.
