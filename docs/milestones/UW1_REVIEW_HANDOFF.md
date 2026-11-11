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

Ran the repository layout and project standards checks, and the full
unittest suite using Python 3.14.5. All 86 cases completed: 83 passed and
three optional PyTorch cases skipped. The initial sandboxed run could not
run local sockets or Windows Git Bash subprocess tests; the repeat with
local test permissions passed, including v1, v2, and signed v3 compatibility.
No external service was needed.

Ran the 10-repeat benchmark across four dimensions, 1,000 trials per listed
adversarial case and challenge setting, and 1,000 honest tasks each at d=16
and d=64 with both provers. The d=128 and d=256 benchmark fixtures passed;
their large correctness sweeps and cross-environment reproduction are open.

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
A correct update can worsen held-out loss; this does not test or solve
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

At d=256, verification took 46.01 ms (3.70% of canonical proving and
6.74% of optimized proving). The slowest measured malformed case took
6.65 ms, 0.974% of optimized proving against a 1% threshold. The packet
is 786,510 bytes. The report records raw timing samples and traced memory.
The decision is INCOMPLETE / NO-GO PENDING EVIDENCE. The held-out run contains 50 accepted steps; 21 worsened loss
relative to the previous step. Only CPython exact CPU arithmetic was
measured. Attempts are local and volatile, and a separately trusted
transcript digest is required for integrity checking. A new verifier
instance has no shared attempt state.
