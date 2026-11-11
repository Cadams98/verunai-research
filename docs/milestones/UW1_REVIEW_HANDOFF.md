# Draft PR: Add the UW-1 commit-then-challenge research verifier

## Purpose

Measure whether a verifier can check an exact integer training result at a
fraction of the cost of computing it. This is a standalone local experiment.
No consensus, rewards, wallet, mining or networking code changes.

## Implementation

Add corpus-derived tasks, canonical and optimized exact provers, a
fixed-width submission format, fresh CSPRNG challenges after commitment,
bounded attempt accounting, projected matrix checks, deterministic transcript
replay, and independent held-out scoring. Both provers generate identical
packets on the tested tasks. The local eligibility flag only records the first
accepted result for an issued scope.

## Testing

The repository layout and engineering standards checks passed. On Windows
with CPython 3.14.5, `python -m unittest discover -s tests -v` ran 91 cases,
with 88 passed and three optional PyTorch skips. The suite includes v1, v2,
and signed-v3 compatibility, the UW-1 adversarial regressions, exact signed
bounds, content-disjoint splitting and an independent scalar oracle.

The corrected Windows campaign accepted 1,000/1,000 tasks per prover at
each of d=16, 64, 128 and 256, with byte parity and no failures. Python 3.10
and 3.12 Linux reproduction remains open. The research report links the
manifests, commands and updated adversarial evidence.

## Documentation

See the [UW-1 report](../USEFUL_WORK_UW1.md) for commands, protocol bounds,
assumptions, measured results and the decision. The report links the raw JSON
benchmark, adversarial and partial honest evidence. The README, architecture
map and changelog cover the research entry point and isolation boundary.
There is no adopted reward architecture, so no ADR establishes one.

## Security and safety

### Affected people

The experiment affects local researchers and reviewers. It collects no
participant data and creates no real rewards, public nodes or user service.

### Privacy and consent

Tasks use the repository's embedded corpus with synthetic scope labels.
There are no credentials, user records, private prompts or external providers.
Transcript digests provide neither confidentiality nor public authenticity.

### Data and model poisoning

The corpus is fixed and the experiment checks mathematical consistency.
The corrected split holds out distinct encoded inputs. Half of the 50 correct
steps worsened the previous held-out loss, and final loss exceeded baseline; this does not test or solve
poisoning, data provenance for outside contributions or model release safety.

### Misinformation

The report separates proving, verification, the ledger's hash lottery, and
held-out performance. It distinguishes the per-attempt bound, repeated
independent probability and observed false accepts. No security level for a
decentralized system or real-world usefulness is claimed.

### Accessibility and fairness

The commands use ordinary CPU Python with no accelerator requirement.
Only one host was measured. Verifier timings do not establish competitive
fairness, Sybil resistance or equal access.

### Energy

The evidence records wall time, packet sizes and traced Python memory.
Power and energy were not measured; runtime ratios are not energy estimates.

### Independent safety review

Claude's independent security review and the safety-reviewer assessment are
pending. Reviewers should examine task scope ownership, commit order,
conditional sampling, replay trust, bounded decoding and the difference
between arithmetic correctness and usefulness.

### Stop-ship conditions

No merge without both independent reviews and founder approval. No
reward-channel work may proceed on the current incomplete evidence.
Unexpected false accepts outside the stated model, stale or duplicated
eligibility, or a fixed acceptance-gate failure also stop advancement.

## Performance and limitations

At d=256 full verification took 39.21 ms, and the slowest malformed
fixture took 4.00 ms (0.52% of optimized proving against
the 1% limit). A well-formed dishonest result took 39.32 ms
to reject. The packet is 786,510 bytes. The report links the wall time,
CPU and traced allocation samples. The prototype holds attempts in memory.
A separate trusted issuer must own task provenance, current head and model
state, authenticated assignment, the cross-instance budget, replay state and
one-time eligibility decisions. Transcript integrity needs a separately
trusted digest. The decision remains INCOMPLETE / NO-GO PENDING EVIDENCE
until the cross-environment correctness evidence is available and all
fixed gates pass.
