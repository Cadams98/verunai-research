# UW-2: can useful learning be verified cheaply?

**Conclusion: INCONCLUSIVE.** In these experiments, none of the specific
no-work strategies tested was credited when each update was scored on a fresh
evaluation batch. That result holds only for workers who cannot see or predict
the evaluation data, which this prototype assumes and does not enforce. The
experiments also demonstrate four limits, two of which look fundamental. This
is a local, TEST-only research prototype with one trusted coordinator and one
trusted data source. It is not a reward system, not consensus, not a security
result, and not secure decentralized Proof of Useful Work.

Raw evidence: [`evidence/uw2_results.json`](../evidence/uw2_results.json),
unchanged since it was first recorded. Code: `verunai/uw2/`. Tests:
`tests/test_uw2.py`.

An AI agent (Claude) designed and implemented this experiment and wrote this
report. Codex independently reproduced the experiments and requested the
corrections in this revision. The owner decides on any merge.

## 1. The question and the plan

> Can independent participants contribute computations that measurably improve
> a model, while others verify those contributions much more cheaply than
> reproducing them, and while workers who contribute nothing earn nothing?

UW-1 showed that an exact calculation can be *checked* cheaply. Its own
held-out result got worse, because a correct calculation is not the same as a
useful one. UW-2 starts from the other end: define usefulness first, then ask
what it costs to verify.

**Definition of useful learning used here.** An update is useful if the model
predicts labels of *fresh examples it could not have trained on* better after
the update than before. "Better" is measured as net wins: examples the new
model gets right and the old one got wrong, minus the reverse.

Hypotheses, written before running the experiments, and what happened:

| # | Hypothesis | Result |
| --- | --- | --- |
| H1 | Updates that contain no real learning are accepted no more often than the test's stated per-test limit | **Not contradicted** (E2). The sample is far too small to confirm the limit itself. |
| H2 | A reused or public evaluation set can be gamed without any training data; fresh batches cannot | **Partly supported** (E3): the reused set was gamed; my public-set attack fell just short; one attacker was tried against fresh batches |
| H3 | Splitting one update across identities earns nothing extra under a proportional reward | **Not contradicted for the one split tested** (E4) |
| H4 | Verification costs a small fraction of the training it checks | **Only when training is large relative to the evaluation batch** (E6, E7) |
| H5 | Verified per-update collaboration learns about as well as pooling all data | **Refuted** (E1): small honest improvements are mostly rejected |
| H6 | An accepted update cannot carry hidden harmful behaviour | **Refuted** (E5): a backdoored candidate was accepted on all 30 batches it was scored on |

## 2. What this experiment models, and what it does not

Read this section before the results.

**Disjoint is not secret.** Training shards, evaluation batches and the test
set come from separate hash streams, so they share no examples. But every
stream is a deterministic function of one seed, and the seed
(`uw2-evidence-v1`) is published in the evidence file so that the results can
be reproduced. The "beacons" used in the experiments are also recorded labels,
not live randomness. **Anyone who has the seed can reconstruct the teacher,
every evaluation batch and the test set** (a unit test demonstrates this).

The attackers in the experiments are written not to use that knowledge. They
see only their own training shard and the published scores. So the experiments
model **workers whose data access is restricted**. They do **not** establish
security against an adaptive worker who knows the seed, predicts the beacon, or
otherwise learns evaluation data in advance. Such a worker could fit the batch
it will be scored on. A live system would need real secrecy and real
unpredictability from a component this prototype does not have.

**What "1 in 1,024" means.** The acceptance test limits the chance that *one*
test accepts an update that does not help, and only under these conditions:

1. The evaluation batch was drawn independently of the update, after the update
   was fixed, and was unknown to its author.
2. The batch is a set of independent draws from the distribution the model is
   meant for.
3. "Does not help" means a changed prediction is no more likely to be a win
   than a loss.

It is **not** a system-wide security bound:

- **Repeated attempts.** Over q submissions the expected number of false
  acceptances can reach q ÷ 1,024. Roughly 700 attempts give an even chance of
  at least one.
- **Multiple identities.** Names are free labels here, so identities simply
  multiply attempts. Nothing in the prototype charges for a submission.
- **Selection.** Accepted updates are the ones applied and credited, so false
  acceptances accumulate in the model instead of averaging out.
- **Adaptive workers.** A worker can use the published scores of earlier
  submissions to choose later ones. Fresh batches keep each single test valid
  under condition 1, but they do not limit how many tests a worker takes.
- **Evidence.** Zero acceptances in 400 trials give a one-sided 95% upper
  confidence limit of about 0.75% per attempt. That is consistent with a limit
  of 0.098% and far too coarse to confirm it. The limit is a property of the
  test under the conditions above, not something these experiments measured.

**Repeated measurements.** Unless stated otherwise, a row such as "30 of 30"
means **one fixed update scored on 30 independent fresh batches**. It estimates
how reliably that one candidate is accepted. It is not a sample of
independently trained updates or independent attacks.

## 3. Architectures considered

| | Architecture | Verifies | Verifier cost | Why it fails or gets expensive |
| --- | --- | --- | --- | --- |
| A | **Exact step verification** (UW-1 Freivalds; refereed delegation such as Verde) | That a prescribed calculation was done correctly | Low for matrix products; dispute games need bit-identical arithmetic on all hardware | Correct is not useful (see E7 for exactly what that experiment does and does not show). The task issuer must also be trusted to pick useful work. |
| B | **Cryptographic proof of training** (zero-knowledge ML) | Same as A, without re-execution | Very low to verify; proving is reported at thousands of times the training cost | Same gap, plus prover cost. |
| C | **Proof of improvement on fresh evaluation** (selected) | The *effect* of an update on unseen data | One evaluation pass per update, independent of how the update was made | Needs fresh labelled data nobody could train on; cannot see hidden behaviours; cannot resolve small gains cheaply. |
| D | **Bundled improvement** (verify the average of all updates once per round) | The effect of the group | One evaluation per round | Free riders are credited; one poisoner blocks everyone (E1). |
| E | **Peer-supplied evaluation data** (workers commit evaluation examples in advance) | As C, without a central data source | As C | Whoever supplies evaluation data can sell answers. E8 measures one such attack. |

| Criterion | A exact step | B zk proof | C fresh improvement | D bundle | E peer data |
| --- | --- | --- | --- | --- | --- |
| Credits only useful work | No | No | **For visible behaviour, given honest data and beacon** | Group only | If data is honest |
| No-work strategies tested here | n/a | n/a | **None credited** | Free rider credited | Depends on collusion |
| Feasible in pure Python now | Yes (UW-1) | No | **Yes** | Yes | Yes |
| Verification cost | Low | Lowest | Moderate, set by statistics | **Lowest** | Moderate |

C was selected because it is the only one that targets usefulness directly.
D and E were then tested as variations, and A is compared in E7.

## 4. The selected design

One round (`verunai/uw2/protocol.py`):

1. The coordinator announces the round number and the fingerprint of the
   current model.
2. Each worker sends a **commitment**: a hash of the round, the model
   fingerprint, its own name, its update and a secret salt. This fixes the
   update without revealing it.
3. After commitments close, a random **beacon** is drawn.
4. Workers **reveal** their update and salt. A reveal that does not match the
   commitment is refused.
5. Updates are processed in an order derived from the beacon. Each one is
   scored against the *current* model on **its own fresh evaluation batch**
   derived from the beacon and the commitment. The update is applied only if
   the acceptance test passes. Its score is its net wins.

**The acceptance test** (`stats.py`). Only examples where the two models
disagree matter. The update is accepted only if the chance of seeing that many
wins by luck is at most 1 in 1,024, computed with exact integers. Section 2
states what that figure does and does not guarantee.

**Workers may train however they like.** Only the submitted integer update and
its measured effect matter.

**Arithmetic recomputation** (`recompute_arithmetic`). Evaluation is exact
integer arithmetic. Given a round record, the starting model, the revealed
updates and the oracle, anyone can recompute every score, decision and the
final model fingerprint. This is an arithmetic consistency check **under
trusted inputs**. It does not authenticate the record: it does not check that
the beacon followed the commitments, that reveals match commitments, or that
the record is the one the coordinator produced. A unit test shows that a
fabricated but internally consistent round passes. It also needs the oracle,
whose seed discloses the evaluation data, so public re-checking and a secret
data source pull against each other. That tension is unresolved here.

**What the protocol does about reuse.** A commitment binds its round number,
model fingerprint and worker name, so within one round object a reveal cannot
be swapped or copied (unit tests). There is **no** persistent state, signature
or log. A unit test shows that a second coordinator accepts the same material
again. No cryptographic or protocol-level replay protection was tested.

**Auditing the evaluator** (`audit.py`). A second validator can check a first
evaluator's published score matrix with a Freivalds-style check instead of
recomputing it. This is where UW-1's technique fits: it verifies the
*evaluation*, not the training.

### Threat model

Workers may submit anything and use many names. **They are assumed not to know
the oracle seed or the beacon in advance** (section 2). Assumed honest:

| Trusted component | What breaks if it is dishonest or leaks |
| --- | --- |
| **Data oracle** (creates and keeps evaluation data) | Everything. Whoever knows evaluation data in advance can be accepted without learning (E8). |
| **Beacon** (randomness after commitments) | A predictable beacon lets a worker pick favourable batches before committing. |
| **Coordinator** (ordering, bookkeeping, applying updates) | Censorship, reordering, false or repeated records. |
| Worker names | They are labels. No authentication, stake, fee or Sybil resistance. |

Out of scope: networking, consensus, payment, privacy of updates, limits on
submissions, rollback of an accepted update, and denial-of-service.

## 5. Data and disjointness

All data is **synthetic** and generated in `verunai/uw2/data.py` from SHAKE-256
streams. No external dataset, personal information or licensed material is
used. The task is a hidden "teacher" linear classifier with 24 integer features
and 6 classes; one label in eight is replaced by a random class.

The harness counts shared feature vectors across training shards, evaluation
batches and the test set in every verified condition: **0 overlaps**. "True
accuracy" always means accuracy on a 20,000-example test set that no worker
strategy and no acceptance decision uses. Attackers choose their trigger class
from their own training shard. Section 2 explains why disjoint streams are not
the same as secret data.

## 6. Results

Reference points: chance 17.7%, best possible (teacher) 89.3%, one worker alone
80.2%, all data pooled centrally 84.4%.

### E1. Collaboration (4 workers, 5 rounds, 5 runs)

The five runs use the **same** training shards and differ only in the recorded
beacons, so they vary the evaluation batches and processing order, not the data.

| Condition | Final true accuracy (mean) | What happened |
| --- | ---: | --- |
| Per-update verification, all honest | 82.3% (80.8–84.0) | First update accepted; most later ones rejected as too small to certify |
| Per-update verification, 1 wrong-label worker | 81.6% (80.8–82.5) | That worker's update was rejected in every round of every run |
| Bundle verification, all honest | **85.2%** | Matches unverified averaging; one test per round |
| Bundle verification, 1 free rider | 82.5% | **Free rider was credited the same score as each honest worker (247)** |
| Bundle verification, 1 wrong-label worker | **17.7%** | **Every bundle rejected; nobody learns or is credited** |
| Unverified averaging, all honest | 85.2% | Simple baseline, no checks |
| Unverified averaging, 1 wrong-label worker | 61.8% | Model badly damaged |

Scope: this shows that **one crude poisoning strategy** (training on labels
shifted by one class) was rejected here. It is not evidence of general
poisoning resistance. E5 is a poisoning attack that succeeds.

H5 is refuted: per-update verification captured only part of the available
learning (82.3% against 85.2%) because of the resolution limit in E6.

### E2. Worthless updates (400 fresh-batch trials each)

For the first three rows, one fixed update is scored on 400 fresh batches. For
the noise rows, each trial uses newly generated noise.

| Update | Accepted at 1/1,024 | Accepted at 1/16 (limit 25) | True accuracy change |
| --- | ---: | ---: | ---: |
| All zeros | 0 | 0 | 0 |
| Re-applying the numeric update already contained in the model | 0 | 0 | 0 |
| Correct training procedure on wrong labels | 0 | 0 | −76.4% |
| Sparse tiny noise | 0 | 3 | +0.01% |
| Dense small noise | 0 | 11 | −0.04% |
| Dense large noise | 0 | 0 | −25.3% |

- The second row is stored in the evidence under the key
  `replay_accepted_update`. It tests **re-applying a numeric update**, which
  leaves this model's predictions unchanged. It is **not** a test of
  cryptographic or protocol-level replay protection (section 4).
- "True accuracy change" is the mean over the first 5 trials of each row. The
  evidence stores that aggregate, not per-trial values.
- 0 of 400 gives a 95% upper limit of about 0.75% per attempt for each of these
  specific strategies. It does not confirm the 1-in-1,024 limit (section 2).
- The 1/16 level was included only to check that the test behaves as
  calculated.

### E3. Gaming the evaluator with no training data

One attacker, with **no data**, submits random changes and keeps those whose
published score went up. Each row is a single run of that attacker.

| Evaluation design | Result on that design | True accuracy change | Same update on a fresh batch |
| --- | --- | ---: | --- |
| Hidden set, reused, scores published (400 queries) | 11 wins, 0 losses: **accepted** | −0.41% | 1 win, 12 losses: rejected |
| Public fixed set (4,000 offline tries) | 10 wins, 1 loss: not accepted (just short) | −0.24% | 10 wins, 15 losses: rejected |
| Fresh batch per submission (400 queries) | Attacker believed +6; final 9 wins, 10 losses: rejected | −0.24% | n/a |

A reused evaluation set leaked enough through its scores for this attacker to
get a harmful update accepted. Against fresh batches this one attacker failed
in this one run. That is a single observation, not a bound on adaptive attacks.

### E4. Splitting one update across six names (30 repeats)

One honest update was split into six pieces touching disjoint groups of
features, submitted in sequence. Each repeat uses fresh batches.

| Credit rule | One submission | Six pieces |
| --- | ---: | ---: |
| Proportional to net wins | 947.4 (sd 21.2) | 948.8 (sd 50.4) |
| Fixed credit per accepted update | 1.0 | **6.0** |

Under proportional credit the split earned **the same total credit** as the
whole, not zero and not more: the mean difference was +1.4 with a standard
error of 10.3. So no advantage was detected **for this one way of splitting**.
This is not proof of Sybil resistance. Untested: other ways of splitting, many
names each submitting noise to collect false acceptances (section 2), and names
used to influence processing order. A fixed credit per acceptance is plainly
exploitable.

### E5. A backdoor that passes (counterexample)

Starting from a 62.5% model, a worker trains once on its real data plus copies
stamped with an out-of-range "trigger" and labelled with a class of its choice.
Each row is **one update scored on 30 fresh batches**.

| Update | Accepted | Mean score | Clean accuracy change | Triggered inputs sent to the attacker's class |
| --- | ---: | ---: | ---: | ---: |
| Honest | 30 / 30 | 243 | +15.8% | 0.02% |
| **Backdoored** | **30 / 30** | 155 | +10.2% | **61.1%** |
| Trigger only, no learning | 0 / 30 | n/a | −0.2% | 3.9% |

H6 is refuted by this counterexample: this backdoored candidate was reliably
accepted (95% lower confidence limit on its acceptance rate: about 90%). The
30 evaluations are of a single trained candidate. They do not measure how often
independently trained backdoor attempts would succeed.

### E6. The resolution limit

One honest update per row, each scored on 100 fresh batches per batch size:

| True gain | 250 | 500 | 1,000 | 2,000 | 4,000 | 8,000 | Predicted size for 50% |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +24.3% | 100% | 100% | 100% | 100% | 100% | 100% | 44 |
| +16.1% | 95% | 100% | 100% | 100% | 100% | 100% | 90 |
| +10.4% | 72% | 100% | 100% | 100% | 100% | 100% | 169 |
| +5.6% | 30% | 81% | 100% | 100% | 100% | 100% | 312 |
| +2.5% | 5% | 12% | 40% | 81% | 100% | 100% | 1,181 |

The batch needed grows roughly as (share of examples that change) ÷ (true
gain)², times about 9.5 for the 1-in-1,024 level. Halving the improvement to be
certified roughly quadruples the evaluation work.

### E7. Cost: exactly what was measured

| Quantity | Measured |
| --- | ---: |
| Worker training (3,000-example shard) | 16,800 example passes, 104.1 ms |
| Verification (1,500 fresh examples, two models) | 3,000 passes, 20.3 ms including data generation |
| **Verification ÷ training** | **17.9% by passes, 19.5% by time** |
| Second validator's audit ÷ first evaluator's work | 30.5% by time (20.8% by multiplications) |
| Update size | 576 bytes |

Method and scope:

- **Timing.** One process, pure Python, one Windows machine. Each figure is the
  median of 5 wall-clock runs after 1 warm-up run. No CPU-time, memory or
  energy measurement, and no control of background load.
- **Training** is the honest worker's whole procedure: three step sizes, two
  passes each, plus its own validation.
- **Verification** is generating the 1,500-example batch plus evaluating both
  models on it.
- **Excluded:** hashing commitments, encoding and decoding updates, drawing the
  beacon, ordering, bookkeeping, arithmetic recomputation, any networking, and
  the cost of producing or protecting the evaluation data in a real system.
- **The audit figure** compares checking two published score matrices with
  computing them. It excludes transmitting the matrices and drawing the
  challenge.
- **"Example passes"** are counted from the procedure, not measured.
- **Projection, not measurement:** if the training shard were 4, 16 or 64 times
  larger with the same batch, the pass ratio would be 4.5%, 1.1% or 0.28%.
  Nothing at those sizes was run.
- "Full re-execution" is taken to cost the same as training; it was not timed
  separately.

In this toy setting the ratio is not impressive. E6 shows that certifying the
+2.5% update reliably needs about 4,000 passes, a quarter of the training that
produced it.

**Correct but harmful.** E7 runs the honest training procedure exactly, but on
labels shifted by one class. Recomputing it gives a bit-identical update, it
lowers true accuracy by 76.4%, and the improvement test rejects it with 33 wins
against 1,178 losses. This shows only that **an exactly reproducible
calculation can be harmful when its inputs are bad**. It does **not** show that
UW-1 would accept an incorrect result, or a result for a task bound to
different data. UW-1 binds each task's data and model, and nothing here was run
through UW-1.

### E8. If the attacker supplies some of the evaluation examples

One trigger-only update per row, tuned by the attacker on its own data and
scored on 30 fresh batches in which a share of examples is attacker-authored.

| Attacker's share of the batch | Accepted | Mean net wins | True accuracy change |
| ---: | ---: | ---: | ---: |
| 0–5% | 0 / 30 | about +1 | +0.05% |
| 10% | 0 / 30 | +24.6 | −8.7% |
| 20% | **30 / 30** | +185.3 | **−8.7%** |

With a fifth of the evaluation data, this update was credited on every batch
while damaging the model. This is one crude attack. A different attack could
need a smaller or larger share; that was not measured.

## 7. What the evidence supports, and the limits found

Supported, for workers who cannot see or predict evaluation data:

- The zero, noise, re-applied and wrong-label updates tested were not accepted
  in 400 trials each.
- One wrong-label worker was rejected in every run, where unverified averaging
  was badly damaged.
- One feature-block split earned no detectable extra credit under proportional
  scoring.
- One query attacker beat a reused evaluation set and failed against fresh
  batches.
- Verification work depends on the batch size, not on how the update was made.

Not established by this work: security against a worker who knows the seed or
beacon; a system-wide false-credit bound; replay protection; Sybil resistance;
general poisoning resistance; cost at any scale other than the one measured.

Limits, in order of seriousness:

1. **Fresh labelled data needs a source nobody can corrupt or predict
   (looks fundamental).** Here that is a trusted oracle with a published seed.
   E8 shows what one partly dishonest source cost.
2. **Outcome checks cannot see hidden behaviour (looks fundamental for this
   design).** E5 is a concrete counterexample.
3. **Small improvements cannot be certified cheaply (statistical).** Evaluation
   grows with the inverse square of the gain.
4. **Attribution against robustness.** Per-update checks give credit to
   individuals but reject small honest work. Bundles learn more and cost less,
   but credit free riders and let one bad update block the round.
5. **The cost advantage is conditional** on training being large relative to
   the evaluation batch.

Approaches that failed along the way: the plain perceptron stalled at about 59%
under label noise and was replaced by an averaged version; my first attack
implementations were too weak to defeat even the baselines and were rewritten;
an unverified *sum* of updates collapsed for unrelated reasons and was replaced
by averaging as the fair baseline.

Remaining uncertainties: one synthetic linear task; one machine; pure Python;
no real dataset; a handful of hand-written attackers; mostly single candidates
re-scored, not independent attacks; no submission cost, cap or rollback.
Published work on adaptive holdout reuse, backdoor poisoning, robust
aggregation and data valuation is relevant and was not re-verified here.

## 8. Can this work in a decentralized setting?

Not as it stands. The arithmetic of evaluation is deterministic and cheap to
recompute. The open problems are not arithmetic: where secret, fresh labelled
data comes from, who draws the randomness, how histories are authenticated, how
attempts are limited, and how to handle behaviour evaluation cannot see. This
design is at most a component for a network with a **trusted or committee-run
evaluator**. It provides no consensus security.

## 9. Proposed next experiment (not implemented here)

**UW-3: replace the single trusted oracle with independent data committers and
measure what collusion costs.** K committers each commit a hidden evaluation
shard before a round and reveal it after updates are committed. Attacker code
must receive committer secrets only through an explicit "colluder" interface,
so that restricted access is enforced by construction and not by convention.

Fixed before running (seeds, sample sizes and analysis included):

| Aspect | What is tested | Criterion |
| --- | --- | --- |
| Collusion | **25% of committers collude** with the attacker (primary condition). 0%, 12.5% and 37.5% are reported as secondary. K = 8 and 16. | All criteria below are judged at 25%. |
| Finite attempts | An attacker budget of 1,000 submissions spread over up to 50 names per campaign. | Total false credit over the whole budget ≤ 1% of the credit honest workers receive in the same campaign. |
| Confidence | At least 3,100 independent no-learning attempts. | Zero acceptances are needed to support a per-attempt rate below 1 in 1,024 at 95% confidence. Any acceptance is reported with an exact interval. |
| Adaptive attacks | Attackers that use published scores, colluders' shards, and the choice of which committers to target. | Same false-credit criterion. Each attacker is specified before the run. |
| Honest acceptance | At least 200 **independently trained** honest updates with true gain ≥ 5%. | Accepted ≥ 80% of the time, with the 95% lower limit ≥ 70%. |
| Backdoors | At least 30 **independently trained** backdoored updates. | Reported, not a pass condition. The design is not expected to stop them, and no backdoor resistance may be claimed from this experiment. |
| Total cost | Committing, revealing and generating all committers' data, every evaluation, and every extra per-committer test. | ≤ 2× the UW-2 verification cost measured the same way. Absolute figures reported. |

Outcome wording is fixed in advance: **"supported for the tested conditions"**
if every criterion is met, otherwise **"not supported for the tested
conditions"**. A negative result would mean that *this* committer scheme, with
these defences and parameters, failed. It would not prove that decentralized
evaluation is impossible, and a positive result would not prove it secure.

A separate step is to repeat E1–E6 on a real, permissively licensed dataset
with a provenance record, after a safety review of that data.

## 10. Reproduce

```powershell
python -m verunai.uw2.experiments --output my-uw2-results.json   # about 6 minutes
python -m verunai.uw2.experiments --quick --output my-quick.json  # about 5 seconds
python -m unittest tests.test_uw2 -v
```

All numbers except the timings in E7 are identical on every run and platform:
data comes from hash streams, training is integer arithmetic, and the beacons
in the experiments are recorded values. That reproducibility is exactly why the
evaluation data here is not secret (section 2). A live round draws its beacon
from the system's secure random generator. Reference environment: Windows 11
build 26300, CPython 3.14.5, Intel family 6 model 183 with 28 logical CPUs,
single process, no GPU. Energy was not measured.
