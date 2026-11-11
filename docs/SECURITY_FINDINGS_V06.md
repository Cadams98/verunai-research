# v0.6 research threat-model and findings

All severities here describe risks to any **hypothetical real network**, not exploitation of a real token. No public Verunai mainnet exists.

## Critical: AI work is not yet an efficient proof of work

The node's `neural-v3` block hash commits to a miner-supplied gradient digest, model digest and nonce. A miner can perform the required canonical training calculation, but an attacker can also guess **invalid** gradient and model digests, mine an otherwise valid SHA-256 header, and send it to a validator. The validator checks the header and difficulty, then recomputes the whole neural gradient before rejecting the fake. This is an asymmetric resource-exhaustion attack. The regression test `test_fake_gradient_rejected_even_if_hash_target_met` shows that forgery is rejected, **not** that the verification cost is affordable.

On top of that, `X^T(XW-Y)` has exploitable mathematical structure; nonce-specific sufficient statistics can in principle be cached or computed more cheaply. The benchmark does not certify minimum work per valid block. Future designs need independent cryptographic review of whether actual AI work is inseparable from winning, and whether proof verification is much cheaper than producing it.

## Critical: not a secure public peer-to-peer network

There is no authenticated peer transport or independent adversarial consensus. HTTP nodes should bind to localhost or be used only on a restricted test LAN. Never open node ports to the Internet, expose them behind a reverse proxy, or accept unknown peers with real assets.

## High: no resilient chain security

The chain accepts the longest *height* with a hash tie breaker, not a rigorously defined cumulative-work rule. Difficulty is fixed and trivially low for testing. It has no finality guarantees, Sybil resistance, safe network partitions, difficulty adjustment, rate limits, or defense against a coordinated hostile miner.

## High: no secure production key management

Wallet secrets are plain text for local disposable identities. They can be lost, copied, or exposed by malware. There is no encryption at rest, hardware wallet support, recovery or safe key rotation. Signatures correctly reject obvious forged transfers in unit tests, but this is not a third-party cryptographic audit.

## Medium: transaction propagation limitations

A transfer is admitted only if it can be applied to the current chain state and current pending transfers; out-of-order transactions are not queued. Mempool is in-memory. Nodes only relay accepted transactions via best-effort HTTP; transaction propagation is not guaranteed. Transactions confirmed on an orphaned branch are not automatically re-queued. Transaction inclusion and eventual confirmations are not guaranteed. No real fees market.

## Medium: bounded but unaudited resource use

The node limits body sizes, block transfer counts, saved chain replay lengths, and model weight magnitudes. This is insufficient against CPU/GPU denial of service, storage exhaustion, malformed traffic, peer eclipsing, or large-scale public exposure. **Never ship it as a production network.**

## Near-term review priorities

1. Attack the candidate generation work factor: derive fastest possible nonce gradient digest and compare to the honest miner.
2. Formally specify consensus math and canonical serialization, separating computational proofs from chain rewards.
3. Evaluate verifiable-computation techniques (probabilistic checking, succinct arguments) with independent cryptographers, including proof generation costs.
4. Add hardened transport, peer authentication, admission limits and signed p2p messages before any wider private testnet.
5. Assess open AI model/data governance, harmful training-data injection, licensing and community oversight.
6. Seek external review before anything with transferable value, financial marketing or custodial key handling.
