# UW-1: verifying a training result after commitment

**Decision: INCOMPLETE / NO-GO PENDING EVIDENCE.** Cross-environment
reproduction is required before considering any reward-channel design.

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
target scale, model digest and corpus digest. The corrected task domain is
`UW1/task/v2` so earlier commitments cannot be used for a corrected task.
The result wire format stays the same. For each dimension, the issuer encodes
all distinct three-character examples from the embedded corpus, then deduplicates
identical encoded feature and target pairs. The first byte of the domain-separated
feature hash places values below 51 in the evaluation pool and the remainder in
training. Grouping by encoded features keeps even input collisions in one pool.
SHAKE-256 selects training examples with replacement only from the training pool.
The next character selects a bucket with target 24. Tests check both pair
and feature disjointness at all four dimensions.


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

The verifier charges one attempt and checks exact byte type, length and task
header. It hashes the bounded payload through a view before unpacking integers.
A wrong digest is rejected without allocating decoded cells. For a matching
digest it unpacks each signed integer section once, checks the full bounds,
and builds row tuples only after every section passes. Only then does it
record the commitment and draw challenges. The submitted bytes and decoded
tuples are immutable. The lock serializes attempt counting, commitment,
challenge and local eligibility. An otherwise valid packet always has its
digest checked. A worker can hash arbitrary data, so bounds remain mandatory
and a matching digest is only a commitment to bytes.

## Trusted caller responsibilities

| Responsibility | Caller contract |
| --- | --- |
| Issuance and provenance | Generate tasks from the approved corpus and deterministic rules. Keep a trusted registry of issued tasks and resolve submissions from that registry. A worker-supplied task object is outside the trust boundary. |
| Authoritative head and model | Supply a current head and the associated model from the authoritative state. Retire or invalidate stale tasks according to the caller's head policy. The embedded head label is only a binding. |
| Assignee | Authenticate the submitting worker and verify the worker owns the registered task. An assignee string is an identifier, not a credential. |
| Attempt budget and replay | Keep one authoritative, atomic budget per issued scope. Enforce it across concurrent verifiers, restarts and retries, and retain enough state to detect repeat submissions. Charge malformed requests under that policy. |
| Eligibility | Consume an accepted decision at most once under the same authoritative task state. The local flag is an experimental decision for one verifier, with no payout or consensus role. |

The prototype implements a serialized in-memory budget and eligibility flag
per verifier. Persistent coordination, identity, cross-instance replay
prevention, chain-head freshness and reward execution belong to the caller
and are outside the prototype.

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
Each factor is at most 1/M. Conditioning on a completed draw within the
retry cap does not favor any eligible vector because the rejection rule is
symmetric. Exhausting the cap produces no decision and cannot increase the
probability of acceptance. Thus the per-submission probability is bounded
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
python -m verunai.useful_work.benchmark --repeats 12 --output evidence/uw1_benchmark.json
python -m verunai.useful_work.benchmark --mode adversarial --output evidence/uw1_adversarial.json
python -m verunai.useful_work.benchmark --mode honest --workers 12 --output evidence/uw1_honest_windows.json
python scripts/check_repository_layout.py
python scripts/check_project_standards.py
python -m unittest discover -s tests -v
```

Honest mode defaults to 1,000 tasks per selected width and checks both
provers for byte-identical packets and acceptance. It writes a seed-ordered
manifest SHA-256, timings and any failures. Optional local worker processes
do not change the task order used for the manifest. It prints progress
every 100 tasks and replaces its target only after a complete run. Use
fewer workers on a machine with less available CPU capacity.

On Linux, run the same suite and generate a separate evidence file for each
interpreter. Compare `result[d].manifest_sha256` across runs for every
dimension and verify the task counts and empty failure lists.

```sh
python3.10 -m pip install -e .
python3.10 -m unittest discover -s tests -v
python3.10 -m verunai.useful_work.benchmark --mode honest --workers 4 --output evidence/uw1_honest_linux_310.json
python3.12 -m pip install -e .
python3.12 -m unittest discover -s tests -v
python3.12 -m verunai.useful_work.benchmark --mode honest --workers 4 --output evidence/uw1_honest_linux_312.json
```

The regular Linux CI unit suite checks the Windows known-answer fingerprints
for seeds 0 and 1 at each dimension. It checks both provers and verifies both
submissions for every task. These small fixtures are separate from the
1,000-task manifests.

The earlier `uw1_honest_16_64.json` file describes the original task split.
Compare corrected runs to the corrected Windows manifest only.

### Correctness campaigns

[Raw Windows campaign JSON](../evidence/uw1_honest_windows.json) records
1,000/1,000 matching and accepted submissions for **each prover** at every
dimension. There were zero failures. Elapsed wall times with 12 workers
were 1.41 s, 8.10 s, 54.55 s and 388.67 s at d=16, 64, 128 and 256,
respectively. The full SHA-256 manifest is recorded for each dimension.
The independent scalar oracle also passed at all four dimensions using
both signs of the maximum allowed input weight. The Python 3.10 and 3.12
Linux runs have commands above and remain unexecuted. The requirement for
matching results across environments therefore remains unverified.

### Cost and size

[Raw benchmark JSON](../evidence/uw1_benchmark.json): Windows 11 build 26300,
CPython 3.14.5, Intel family 6 model 183 stepping 1, 28 logical CPUs, one
process, exact CPU integers. No GPU or energy measurements. Each workload
has one warm-up per fixture and 12 timed trials, four on each of three
fixtures. A fixed seed shuffles workload order within each trial. Fixtures
vary the public task and model, and place a correctly hashed out-of-bounds
integer in a different section for each case. Wall time, process CPU time,
range, median absolute deviation, per-fixture medians and traced allocation
peaks are retained in the JSON. Short operations also get separate CPU
batches because Windows CPU ticks are coarser than the wall clock. A null
batch estimate means the clock did not advance, or the operation was long
enough to use per-call CPU timings. Allocations are sampled separately from
timing and exclude prebuilt inputs.

Both provers use the same prebuilt tasks. Corpus encoding and task issuance
happen during fixture setup. There is no precomputation specific to either
prover. Full verification includes attempt charging, framing, hashing,
decoding and bounds checks, commitment recording, fresh challenges,
projection, exact update and transcript construction. Transport, verifier
construction, writing to disk and replay are outside this timing. Honest
submission encoding has its own metric. Incorrect mathematical results
with valid framing, bounds and digests are measured separately from
malformed packets. The malformed gate uses the largest fixture median
across all malformed workloads.

| d | Canonical ms | Optimized ms | Verifier ms | Dishonest math ms | Worst malformed fixture ms | Packet bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 1.597 | 0.891 | 0.596 | 0.575 | 0.037 | 6,222 |
| 64 | 19.989 | 11.848 | 2.744 | 2.756 | 0.254 | 49,230 |
| 128 | 161.510 | 102.279 | 10.951 | 11.158 | 1.146 | 196,686 |
| 256 | 1,140.339 | 768.886 | 39.214 | 39.320 | 4.003 | 786,510 |

At d=256, full verification cost 3.44% of canonical and
5.10% of optimized proving (limits 10% and 25%). The slowest
malformed fixture cost 4.003 ms, or 0.351% of canonical and
0.521% of optimized proving (limit 1%). The malformed gate
passed on this run. The packet passed the decimal 1 MB limit.

A dense wrong digest took 0.322 ms and peaked at
1,265 traced bytes. A correctly hashed
out-of-bounds packet still needs integer decoding and peaked at
7,862,817 traced bytes. Full verification
peaked at 11,142,077 traced bytes and used a median
31.25 ms of process CPU time. The complete
allocation and CPU measurements are in the raw JSON, including separate
CPU batches for short operations. Traced allocations are not RSS.

### Adversarial and held-out results

[Raw adversarial JSON](../evidence/uw1_adversarial.json) records 1,000 trials
per listed case. No default-parameter corrupted submission was accepted.
No deterministic malformed, scope, replay or duplicate case was accepted.
The rank-one parameter sweep saw 2/1,000 false accepts at (8,1) versus about
3.91 expected and zero in the other five settings. Zero in 1,000 independent
trials gives a one-sided 95% upper confidence limit of about 0.30%, far
above the default mathematical bound. The repeated (8,1) experiment saw
8/1,000 successful sessions, with up to three attempts each and 2,990 total
attempts. The independent-session model expects about 11.67 successes and
the union bound is 3/256 per session. The denominators for these results
are sessions or attempts as indicated, never interchangeable.

The finite two-coordinate counterfactual enumerates fixed choice versus
choice after seeing the challenge. The exact population probabilities are
3/15 and 9/15. In the separate 8-bit comparison, the preview was accepted
in 9/1,000 trials and the actual fresh challenge in 5/1,000 trials. The
model predicts about 0.01169 and 0.003906 respectively. These small samples
illustrate the model and are insufficient to establish cryptographic-scale
probabilities. The tests also verify the sampler fails closed when its
bounded draws produce no admissible vector.

At d=16, the corrected training and evaluation pools contain 141 and 27
unique encoded pairs, respectively. The evaluation loss after 50 verified
steps was 16,658 versus an unchanged baseline of 15,552, a **7.11% increase**.
Twenty-five correct steps improved over the preceding step and 25 worsened
it. The loss is an exact sum of squared errors on a toy corpus. Acceptance
validates arithmetic and does not establish beneficial learning.

A sender can recompute the digest of arbitrary bytes, so correctly hashed
malformed values still need bounded decoding. A correctly framed and bounded
dishonest result also incurs the mathematical checks. The in-memory
benchmark does not measure traffic flooding or system-level denial of
service. Attempt enforcement across processes and restarts and trusted
transcript retention remain caller responsibilities. Claude's independent
review, the safety review and founder approval remain separate gates.
