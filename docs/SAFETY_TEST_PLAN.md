# Safety evaluation plan — research backlog (v0.6.3)

**State:** Planned work; no deployed large language model exists in v0.6.3. The existence of this plan and associated repository checks is **not proof of model safety**.

## Trackable research areas

| Area | Test evidence needed | Owner/reviewer |
| --- | --- | --- |
| Knowledge quality | Source-citation checks, unsupported-claim rate, currency of cited material, multilingual evaluation | ML researcher + independent safety reviewer |
| Harmful instructions and misuse | Risk-tiered red-team cases; documented mitigations and residual harms | Safety reviewer + human reviewer |
| Privacy | Canary/leakage tests, prompt retention and consent audit, attempts to expose secrets | Security auditor + safety reviewer |
| Prompt injection and tool control | Malicious retrieved-page and tool-output tests; least-privilege authorization gates | Security auditor |
| Data poisoning and miner manipulation | Corrupted contributions, malicious update simulations, provenance checks, rollback exercise | ML + consensus + security reviewers |
| Fairness and accessibility | Representative, documented evaluation groups and multilingual/accessibility checks | Independent reviewers and impacted contributors |
| Operational resilience | Traffic spikes, denial-of-service, model/service rollback, abuse-rate controls | Network engineer |
| Energy and useful work | Joules or watt-hours per useful unit when measurable; honest vs optimized miners; validator burden | Mining researcher |

## Example baseline acceptance process

1. Register a risk and expected harm **before** adding the related capability.
2. Establish a known-good baseline and disclose the testing environment.
3. Add realistic positive and negative cases; include source, consent, and threat assumptions.
4. Run red-team assessments separately from the implementing agent; retain reproducible, privacy-safe evidence.
5. Review severity, affected people, mitigations and residual uncertainty. Record an explicit go/no-go decision before public deployment.
6. Publish a model card, safety report, and incident/reporting channel when an actual model is selected for release.

Do not paste harmful exploit detail or private personal data into public test artifacts; use synthetic test records. Local code checks can verify the *presence* of safety policies but cannot verify AI behavior or governance fairness.
