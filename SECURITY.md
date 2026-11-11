# Security policy

Verunai is experimental educational software. **There is no production blockchain, secure real-money wallet, or supported public deployment.** No funds should ever be entrusted to it.

Please do not publish exploitable vulnerability details affecting an eventual public testnet before maintainers can respond. For now, if no private contact is provided, report non-sensitive design flaws through GitHub issues and keep sensitive attack details in a private channel agreed with the maintainer.

Priority security research: shortcuts that bypass AI compute, block validation differences, overflow and parsing edge cases, identity spoofing, selfish mining, denial of service, data poisoning, replay attacks, model/data provenance, and reward-accounting bugs.

No bounty program is offered. Do not attack third-party systems or miners.


## Private testnet daemon is not safe on the Internet

The new `python -m verunai node` HTTP API is unauthenticated and unencrypted. It binds to loopback by default. Do not use `--allow-lan` except inside a properly isolated experiment. Do not expose ports, store real assets, solicit mining fees, or connect real-money wallets. Known research issues are listed in `docs/ATTACK_SURFACE.md`.


## v0.6 signed research transactions

The disposable `neural-v3` wallets hold plaintext private signing keys and only
control fictional nontransferable TEST balances. Never use them for real assets
or publish wallet files. The unauthenticated HTTP endpoints are for loopback
or isolated private experiments only. Review `docs/SECURITY_FINDINGS_V06.md`.

The short v3 protocol does NOT solve secure proof of useful AI computation.
False gradient commitments can satisfy hash difficulty cheaply but require
expensive recomputation by validators to reject. This design has serious
resource-exhaustion risks and should not accept external untrusted traffic.

## Responsible AI safety disclosures

Model safety, privacy leakage, training data poisoning, prompt injection, and agent overreach are within project security scope. Consult `docs/SAFETY_AND_ETHICS.md` and `docs/SAFETY_TEST_PLAN.md`. Before a public service is launched, establish a monitored private safety reporting contact and response owner. This repository currently does **not** provide an always-monitored private reporting endpoint; do not imply that it does.
