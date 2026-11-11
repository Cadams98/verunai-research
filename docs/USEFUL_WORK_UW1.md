# UW-1: verifying a training result after commitment

**Decision: INCOMPLETE / NO-GO PENDING EVIDENCE.** The measured d=256 cost and
size gates passed on one Windows host. The 1,000-task correctness sweeps
at d=128 and d=256 and cross-environment reproduction remain open. No reward
channel, protocol change, public service, or model release is authorized.

## What the experiment asks

Can a verifier check a matrix training result more cheaply than a worker can
produce it? UW-1 checks the **result** and accepts any exact algorithm that
produces it. The SHA-256 operation here binds bytes; it is unrelated to the
ledger's SHA-256 mining lottery. The actual computation is two matrix products
and a quantized update. Verification uses matrix-vector products, scans, hashes
and a transcript. Shortcut and caching opportunities are welcome and can
change the cost ratios. The reported approximately 17× neural-v3 shortcut was
an isolated calculation, without verified full-miner throughput.

## Task and wire format

The trusted verifier generates a task for widths 16, 64, 128 or 256, with
n = max(64, d). A domain-separated SHA-256 task digest binds task ID,
assignee, chain-head label, unsigned 64-bit seed, dimensions, update divisor,
target scale, model digest and corpus digest. SHAKE-256 selects training
positions with replacement and expands each public two-character context into
d signed features. The next character selects a bucket with target 24. The
last contiguous corpus split is held out, with a gap; context strings can
still recur across splits. No private inputs or external dataset are used.

Both provers compute E = XW − Y, G = XᵀE and
W_next = W − trunc(G / divisor), where divisor is n × max(1, d/8).
The width, seed, split and divisor differ from the legacy training experiment;
target scaling and truncation toward zero are preserved. Canonical dot
products use a Python generator; optimized dot products use mapped built-in
integer multiplication. Both transpose operands once per product; no offline
precomputation is needed. Neither uses floating-point arithmetic or NumPy.

The packet contains the 14-byte domain marker, 32-byte task digest, exactly
(n + 2d) × d row-major signed big-endian int32 cells for E, G and W_next,
and a 32-byte SHA-256 digest of the preceding bytes. No lengths, counts or
integer widths are supplied by the worker. The input model is bounded at
10,000 per entry, E at 2,560,024 and G at 655,366,144. The submitted update
is bounded by 10,000 plus the gradient bound, then checked exactly. The
trusted task supplies the expected size, shapes and context.

The verifier charges one attempt, rejects invalid lengths, context and
bounds, and recomputes the commitment. Only after storing the attempt number
and immutable digest does it call Python's OS-backed CSPRNG. The submitted
bytes and decoded tuples are immutable, and the lock serializes this sequence
with reward eligibility. The public submit method has no challenge input or
worker callback. Each verifier owns one issued scope and closes on its first
accepted submission or exhausted attempt budget. Malformed attempts count but
generate no challenge transcript. One instance per issued scope is a trusted
caller invariant. Recreating the instance or changing identities can bypass
the local budget. This design assumes trusted task issuance and authenticated
assignment at the application boundary; the assignee label is not a login or
signature. There is no network listener, durable state or actual award.

## Why the check works

For every challenge r, the verifier computes both sides of X(Wr) − Yr = Er
and Xᵀ(Er) = Gr exactly, with unbounded Python integers. If either matrix
relation is wrong, pick a nonzero row of its difference matrix. Once all but
one coordinate of r are fixed, a coordinate with a nonzero coefficient can
have at most one value that makes that row's dot product zero. The exact
update is then checked entry by entry. Honest results pass for every valid
challenge. Incorrect updates fail regardless of randomness.

For b random bits per coordinate let M = 2^b. In the unconditioned universe
of M^d vectors there are at most M^(d−1) passing vectors. The zero vector
always passes a homogeneous linear check. Removing it leaves at most
M^(d−1) − 1 passing vectors out of M^d − 1. The verifier samples uniformly
from the remaining vectors without replacement within a transcript; duplicate
or zero draws are discarded, and 128 draws without enough candidates fail
closed. Given j previous passing draws, the conditional chance is at most
(M^(d−1) − 1 − j)/(M^d − 1 − j), with probability zero if none remain.
Each factor is at most 1/M. Thus the per-submission probability is bounded
by 2^(−bk) for a fixed incorrect commitment and ideal uniform fresh draws.
Checking both relations never raises this bound. Rounds are not strictly
independent after rejecting duplicates. A fresh random session identifier
and attempt number identify records; a vector may coincide by chance in a
different transcript. The normal verifier never imports an old challenge.

Across q attempts, the union bound is min(1, q × 2^(−bk)) if the bound
continues to hold conditioned on prior history. Adaptive workers can use
past outcomes, but must commit before the next fresh draw. If each attempt
instead has exactly the same success probability p and the attempts are
independent, the chance of at least one success is 1 − (1 − p)^q. The
expected **count** over q independent attempts without early stopping is
q × p. These are different quantities. At default parameters b=32 and k=2,
the mathematical bound is 2^−64 per fixed submission under these assumptions;
there is no unconditional security level for a wider system.

## Transcripts and replay

The canonical transcript contains the task context, commitment, session and
attempt metadata, challenge parameters and vectors, both projected sides in
each round, exact update result, eligibility and final outcome. Replay takes
the original task and packet plus a separately trusted digest, and recomputes
the transcript without drawing new randomness. Comparing against the trusted
digest detects changed records. Someone who can replace both the transcript
and its trusted reference can fabricate a consistent history. Replay cannot
prove when or how the randomness was generated, or that earlier attempts
were counted. Public authenticity needs an independently recorded commitment,
authenticated log, trusted signature or equivalent mechanism. Decentralized
challenge timing, randomness, identity, rewards and disputes remain separate
design problems.

## Reproduce the evidence

Run from the repo root with Python 3.10+ and the project dependencies. UW-1
itself adds no dependency. In PowerShell, use the installed interpreter's
full path if the Windows Store alias does not work.

```powershell
python -m verunai.useful_work.benchmark --output evidence/uw1_benchmark.json
python -m verunai.useful_work.benchmark --mode adversarial --output evidence/uw1_adversarial.json
python -m verunai.useful_work.benchmark --mode honest --dimension 16 --dimension 64 --output evidence/uw1_honest_16_64.json
python -m verunai.useful_work.benchmark --mode honest --dimension 128 --dimension 256 --output evidence/uw1_honest_128_256.json
python scripts/check_repository_layout.py
python scripts/check_project_standards.py
python -m unittest discover -s tests -v
```

Honest mode defaults to 1,000 tasks per selected width and checks both
provers for byte-identical packets and acceptance, with a deterministic
aggregate packet fingerprint. Rerun each width on another environment and
compare fingerprints. Omit dimension selection to run all widths. Large runs
are opt-in, limited to 10,000 trials per width, and may be interrupted with
Ctrl+C. Completed dimensions print progress; the JSON replaces its target
only after a complete run. At d=256 the measured proving costs alone suggest
about 32 minutes for 1,000 tasks on this host, before the two checks per task.

### Cost and size

[Raw benchmark JSON](../evidence/uw1_benchmark.json): Windows 11 build 26300,
CPython 3.14.5, Intel family 6 model 183 stepping 1, 28 logical CPUs, one
process, exact CPU integers. No GPU or energy measurements. Each workload
has one warm-up and ten timed trials, with range and median absolute
deviation retained in JSON. Provers share a prebuilt task; task issuance and
transport are outside the timed region. Submission encoding has its own
metric. Full verifier time includes attempt charging, framing and decoding,
bounds and context checks, commitment recording, challenge generation,
projection, exact update, and transcript construction and hashing. Export
to disk and replay are separate operations. Malformed cases cover immediate size rejection, an honest-shaped packet
with the wrong digest, dense integers with the wrong digest, and a dense
packet whose last integer is out of bounds.

| d | Canonical ms | Optimized ms | Verifier ms | Late malformed ms | Packet bytes |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 1.70 | 0.79 | 0.60 | 0.053 | 6,222 |
| 64 | 20.09 | 10.95 | 2.89 | 0.410 | 49,230 |
| 128 | 165.40 | 98.35 | 13.33 | 1.849 | 196,686 |
| 256 | 1,243.66 | 682.88 | 46.01 | 6.653 | 786,510 |

At d=256 the verifier cost 3.70% of canonical and 6.74% of optimized proving
(gates: 10% and 25%). The slower measured malformed case cost 0.535% and
0.974% respectively (gate: 1%); a short packet took 0.0010 ms. The
malformed gate passed by a narrow margin on this host. Packet size
passed the decimal 1 MB limit. The d=256 peak traced allocations in a
separate pass were 5,593,648 bytes for canonical proving, 5,593,816 for
optimized proving and 6,612,920 for verification. The dense wrong-digest
case peaked at 10,004,248 bytes. These count Python
allocations during the operation, excluding prebuilt inputs; they are not
process RSS, GPU memory, energy or network costs. The verifier's storage and
arithmetic scale quadratically at fixed k as d grows here; proving is cubic
with these implementations. No claim about faster workers or aggregate
service capacity follows from these timings.

### Adversarial and held-out results

[Raw adversarial JSON](../evidence/uw1_adversarial.json): 1,000 trials per
listed class. Default-parameter corrupted results produced no false accepts;
deterministic malformed, scope, replay and duplicate cases produced no
unexpected accepts. The rank-one parameter sweep saw 2/1,000 false accepts
at (8,1), compared with about 3.91 expected, and zero in each of the other
five settings. These sample sizes cannot validate cryptographic-scale
probabilities. The repeated (8,1) experiment saw 15 successful sessions in
1,000, with up to three attempts each and 2,987 actual attempts. The
independent-session model predicts about 11.67 successful sessions; the
union bound is 3/256 per session. Neither observed count establishes the
underlying risk. The deliberately tiny two-coordinate, two-bit grinding
counterfactual enumerates a fixed choice before the draw versus choosing
among three error patterns after previewing the vector: 201/1,000 versus
601/1,000 cyclic cases, with exact population probabilities 3/15 and 9/15.
That exhaustive illustration is separate from CSPRNG trials. It explains
why advance knowledge of the challenge breaks the fixed-submission
assumption. A separate 8-bit synthetic comparison saw 9/1,000 accepts
if the preview vector were reused and 4/1,000 when the actual verifier drew
a fresh vector after the selection was committed. For the three coordinate
kernels the preview union has probability about 0.01169; the fresh draw
has probability about 0.003906 for each preselected variant. These are
local fixed-matrix experiments, separate from the ledger.

Over 50 verified d=16 updates, held-out squared loss fell from 273,024 to
251,828 (7.76% below the unchanged no-training baseline). Of the accepted
updates, 28 improved loss relative to the previous step, 21 worsened it,
and one tied. The worsening steps were labeled “no improvement.” This
is a toy corpus split and does not demonstrate real-world usefulness.

The [partial honest sweep](../evidence/uw1_honest_16_64.json) passed for
1,000 tasks at each of d=16 and d=64, with full acceptance and byte parity
for both provers. The full correctness gate remains unverified. Do not
advance to reward-channel design on the current evidence. If the approach
fails the remaining gates, compare refereed delegation or dispute-based
verification. Claude's independent security review, a safety-reviewer
assessment and founder approval are required before merge.
