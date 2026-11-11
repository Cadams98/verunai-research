# Verunai safety and ethics charter (draft, v0.6.3)

**Priority:** Public benefit, human rights, safety, and accountability take precedence over token value, speed, growth, or founder advantage. This document is binding for *Verunai-maintained software, AI services, model releases, development agents, and community processes* while the community works toward independent governance.

**Status:** These are engineering requirements and release gates, **not** claims that the current prototype is safe. Verunai currently has a local experimental blockchain and toy neural training, not a deployed public AI service or a production-grade cryptocurrency.

## Mission

Provide open, accessible, verifiable intelligence in service of all humanity. Make the system understandable, correctable, and accountable. Do not promise unbiasedness, infallibility, or perfect safety.

## Commitments and concrete requirements

1. **Safety and misuse prevention.** Threat-model foreseeable harms before new capabilities or releases. Evaluate misuse potential, dangerous instructions, agent overreach, prompt injection, and insecure tool integrations. For Verunai-maintained AI interfaces, apply proportionate access controls and mitigations. Do not grant agents authority to spend money, deploy models, transact tokens, or change consensus rules without explicit human approval.
2. **Truthfulness and knowledge quality.** Distinguish sourced statements from guesses; show source attribution, freshness and uncertainty when possible. Provide a way to report errors and roll back contaminated knowledge. Maintain evaluation sets including adversarial misinformation and unsupported citations.
3. **Privacy and autonomy.** Collect the least data reasonably necessary; require appropriate notice and consent for training data and telemetry. Do not commit secrets, user prompts, personal data, sensitive documents, or raw identifiable records to a public blockchain. Publish only bounded hashes or commitments when lawful and necessary; **hashes alone do not make personal data safe**. Document deletion/retention and revocation mechanisms for off-chain systems.
4. **Human rights and equitable access.** Test quality and harms across languages, regions, and accessibility contexts to the extent measurable. Do not use the AI to discriminate or to make consequential automated decisions about people without appropriate human oversight and due process. Provide understandable policies, user feedback, and appeals for maintained services.
5. **Data and model provenance.** Use datasets and model weights only when source, license, permissions, and applicable restrictions are understood. Record dataset/model lineage, consent conditions, integrity checks, and known limitations. Validate miner-submitted training/evaluation contributions against poisoning, hidden backdoors, and reward manipulation before allowing any shared model update.
6. **Transparent governance.** Publish safety policies, decision rationales, incident learnings (without sensitive exploit details), conflicts of interest, community feedback routes, and change proposals. Do not give a founder or a token-rich faction an unchecked, permanent power to alter the ledger or change safety policies. Safety changes must be reviewable, contestable, and reversible where technically possible.
7. **Environmental stewardship.** Measure energy use and work that is *actually useful*. Do not describe gratuitous computation as beneficial AI training. Report hardware, throughput, verifier cost, and electricity assumptions with uncertainty.
8. **Accountable incident response.** Maintain a private reporting path before public deployment, severity triage, containment plans, responsible disclosure, postmortems, and criteria to pause Verunai-maintained services or releases when risk exceeds controls. Independent peer software cannot be globally switched off.

## Distinguish three layers: no false promise of central control

- **Consensus protocol:** nodes independently check deterministic block, reward, and signature rules. It cannot universally enforce subjective AI response policies across every user's machine; do not encode sweeping content judgments into consensus.
- **Open model and data releases:** publishing weights can enable forks outside the community's control. Evaluate capability risks and release forms before publishing; 'open source' is not a safety evaluation.
- **Verunai-operated applications and agent systems:** maintained interfaces can implement privacy protection, user controls, moderation, logging with strict retention, tool-permission boundaries, abuse rate limits, and appeals. Those controls don't automatically govern other operators.

Decentralization, free expression, privacy, safety, and permissionless access can conflict. Document the tradeoffs, impacted groups, evidence, community consultation, and alternative approaches. Do not silently claim one principle overrides every other in all contexts.

## Release gates

**All code changes:** readability, tests, documentation, security/safety impact statement; no undisclosed collection of personal data or uncontrolled remote execution.

**Before releasing a trained model or a public AI interface:** documented intended use and limitations; dataset/model provenance; misuse threat model; baseline quality, factuality and bias tests; privacy leakage and prompt-injection tests; independent safety review; incident contact; monitoring/rollback plan for maintained services; publicly documented known risks.

**Before distributed miner training:** verifiable data/work provenance; tests for poisoning and reward gaming; chain/model state rollback or containment strategy; bounded verifier cost; resource measurements and independent adversarial review.

**Before public blockchain/mainnet or valuable token:** independent security review, legal analysis, economic disclosure, secure networking, wallet safety, and explicit owner/community authorization. No current release meets this gate.

**Stop-ship criteria:** known critical exploitable privacy leak, uncontrolled dangerous agent actions, unreviewed model poisoning path, severe unmitigated misuse risk, falsified benchmarks, or an uncontained high-severity security flaw. Record exceptions only after explicit human review and a documented reason; no exception may conceal risk.

## External references (guidance, not certifications)

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST trustworthy AI characteristics: https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/
- UNESCO Recommendation on the Ethics of Artificial Intelligence: https://www.unesco.org/en/articles/recommendation-ethics-artificial-intelligence
- OWASP GenAI and LLM threats: https://genai.owasp.org/llm-top-10/

These references inform our charter. We are not certified, audited or endorsed by these organizations.
