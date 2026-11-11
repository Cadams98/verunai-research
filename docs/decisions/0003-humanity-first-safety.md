# ADR 0003: Human-first public-interest and AI safety requirements

- **Status:** Accepted as contributor/agent policy; safety mechanisms still unimplemented
- **Date:** 2026-11-10
- **Context:** Verunai aims to be a community-owned, permissionless AI computing network. Permissionless mining and publicly available model weights create risks that cannot be erased by an operator's moderation policy.
- **Decision:** Adopt `docs/SAFETY_AND_ETHICS.md` and `docs/SAFETY_TEST_PLAN.md` as required project guidance. Introduce independent safety-review responsibility and explicit safety-impact sections in pull requests. Govern maintained interfaces and model releases by documented evaluations; do not pretend a decentralized protocol can regulate every fork's AI output.
- **Reasons:** The project's mission is service to humanity. Acceleration without provenance checks, privacy controls, and independent reviews risks undermining public trust and harming users.
- **Tradeoffs:** Review slows some releases; some model release forms may need restrictions or staged deployment. Founder direction is provisional until credible community governance develops. These are deliberate limitations, not claims of universal safety.
- **Follow-up:** Implement risk register, model/data lineage, quality and safety evaluation harness, independent review process, security disclosure channel, and governance proposal.
- **Out of scope:** Changes to block consensus; live model deployment; valuable token issuance; certification of safety.
