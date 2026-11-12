# UW-2: can useful learning be verified cheaply?

**Conclusion: INCONCLUSIVE.** Paying for *measured improvement on fresh,
unseen evaluation data* worked against every cheating strategy tested that
tries to earn without contributing. It also has four limits that this
experiment demonstrates rather than hides. Two of them look fundamental. This
is a local, TEST-only research prototype with one trusted coordinator and one
trusted data source. It is not a reward system, not consensus, and not secure
decentralized Proof of Useful Work.

Raw evidence: [`evidence/uw2_results.json`](../evidence/uw2_results.json).
Code: `verunai/uw2/`. Tests: `tests/test_uw2.py`.

An AI agent (Claude) designed and implemented this experiment and wrote this
report. Independent review of the code by another agent or person is still
pending, and the owner decides on any merge.

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
| H1 | Updates that contain no real learning are accepted at most at the stated false-acceptance rate | **Supported** (E2) |
| H2 | A reused or public evaluation set can be gamed without any training data; fresh batches cannot | **Partly supported** (E3): the reused set was gamed, my public-set attack fell just short |
| H3 | Splitting one update across identities earns nothing extra under a proportional reward | **Supported** (E4) |
| H4 | Verification costs a small fraction of the training it checks | **Only when training is large relative to the evaluation batch** (E6, E7) |
| H5 | Verified per-update collaboration learns about as well as pooling all data | **Refuted** (E1): small honest improvements are mostly rejected |
| H6 | An accepted update cannot carry hidden harmful behaviour | **Refuted** (E5): a backdoored update was accepted 30 of 30 times |

## 2. Architectures considered

| | Architecture | Verifies | Verifier cost | Why it fails or gets expensive |
| --- | --- | --- | --- | --- |
| A | **Exact step verification** (UW-1 Freivalds; refereed delegation such as Verde) | That a prescribed calculation was done correctly | Low for matrix products; dispute games need bit-identical arithmetic on all hardware | Correct is not useful. E7 shows an exactly reproducible training step on wrong labels that destroys the model. The task issuer must also be trusted to pick useful work. |
| B | **Cryptographic proof of training** (zero-knowledge ML) | Same as A, without re-execution | Very low to verify; proving is reported at thousands of times the training cost | Same "correct is not useful" gap, plus prover cost. |
| C | **Proof of improvement on fresh evaluation** (selected) | The *effect* of an update on unseen data | One evaluation pass per update, independent of how the update was made | Needs fresh labelled data nobody could train on; cannot see hidden behaviours; cannot resolve small gains cheaply. |
| D | **Bundled improvement** (verify the average of all updates once per round) | The effect of the group | One evaluation per round | Free riders are credited; one poisoner blocks everyone (E1). |
| E | **Peer-supplied evaluation data** (workers commit evaluation examples in advance) | As C, without a central data source | As C | Whoever supplies evaluation data can sell answers. E8 measures how much share an attacker needs. |

Selection, using the same four criteria for each:

| Criterion | A exact step | B zk proof | C fresh improvement | D bundle | E peer data |
| --- | --- | --- | --- | --- | --- |
| Rewards only useful work | No | No | **Yes, for visible behaviour** | Group only | If data is honest |
| Resists no-work earning | Yes | Yes | **Yes, given an honest data source and beacon** | No (free riders) | Depends on collusion |
| Feasible in pure Python now | Yes (UW-1) | No | **Yes** | Yes | Yes |
| Verification cost | Low | Lowest | Moderate, set by statistics | **Lowest** | Moderate |

C was selected because it is the only one that targets usefulness directly.
D and E were then tested as variations, and A is compared in E7.

## 3. The selected design

One round (`verunai/uw2/protocol.py`):

1. The coordinator announces the round number and the fingerprint of the
   current model.
2. Each worker sends a **commitment**: a hash of the round, the model
   fingerprint, its own name, its update and a secret salt. This fixes the
   update without revealing it.
3. After commitments close, a random **beacon** is drawn.
4. Workers **reveal** their update and salt. A reveal that does not match the
   commitment is refused, so nobody can copy a revealed update or change their
   own after seeing the beacon.
5. Updates are processed in an order derived from the beacon. Each one is
   scored against the *current* model on **its own fresh evaluation batch**
   derived from the beacon and the commitment. The update is applied only if an
   exact statistical test says it improved the model. Its score is its net wins.

**The acceptance test** (`stats.py`). Only examples where the two models
disagree matter. If an update does not truly help, each such example is a win
with probability at most one half. The update is accepted only if the chance of
seeing that many wins by luck is at most 1 in 1,024. The calculation uses exact
integers. Because every update gets a batch that did not exist when it was
committed, this limit holds for every submission, however adaptive the worker,
**provided the data source and the beacon are honest**.

**Workers may train however they like.** Only the submitted integer update and
its measured effect matter. Evaluation is exact integer arithmetic, so any node
with the evaluation data recomputes every score bit for bit (`replay`). In this
prototype that data comes from the oracle, whose secret also reveals the
teacher. Public re-checking and a secret data source pull against each other;
that tension is unresolved here.

**Auditing the evaluator** (`audit.py`). A second validator can check a first
evaluator's published score matrix with a Freivalds-style check instead of
recomputing it. This is where UW-1's technique fits: it verifies the
*evaluation*, not the training.

### Threat model

Workers are adversarial and may submit anything, use many identities, replay,
copy, or collude with each other. Assumed honest in this prototype:

| Trusted component | What breaks if it is dishonest |
| --- | --- |
| **Data oracle** (creates fresh labelled examples) | Everything. Whoever knows evaluation data in advance can be accepted without learning (E8). |
| **Beacon** (randomness after commitments) | A predictable beacon lets a worker pick favourable batches before committing. |
| **Coordinator** (ordering, bookkeeping, applying updates) | Censorship, reordering, false records. Replay detects wrong arithmetic, not a dishonest beacon. |
| Worker names | They are labels. There is no authentication, no stake and no Sybil resistance. |

Out of scope: networking, consensus, payment, privacy of updates, and
denial-of-service by flooding.

## 4. Data and disjointness

All data is **synthetic** and generated in `verunai/uw2/data.py` from SHAKE-256
streams. No external dataset, personal information or licensed material is
used. The task is a hidden "teacher" linear classifier with 24 integer features
and 6 classes; one label in eight is replaced by a random class. The best
possible accuracy is therefore below 100%.

Training shards, evaluation batches and the ground-truth test set come from
separate streams. The harness counts shared feature vectors across all of them
in every verified condition: **0 overlaps** (`evaluation_overlap_with_training_or_test`
and `training_shards_and_test_overlap` in the evidence; also a unit test).
"True accuracy" always means accuracy on a 20,000-example test set that no
worker and no acceptance decision ever uses. Attackers choose their trigger
class from their own training shard.

## 5. Results

Reference points: chance 17.7%, best possible (teacher) 89.3%, one worker alone
80.2%, all data pooled centrally 84.4%.

### E1. Does verified collaboration learn? (4 workers, 5 rounds, 5 independent runs)

| Condition | Final true accuracy (mean) | What happened |
| --- | ---: | --- |
| Per-update verification, all honest | 82.3% (80.8–84.0) | First update accepted; most later ones rejected as too small to certify |
| Per-update verification, 1 poisoner | 81.6% (80.8–82.5) | Poisoner rejected every time; earned 0 |
| Bundle verification, all honest | **85.2%** | Matches unverified averaging; one test per round |
| Bundle verification, 1 free rider | 82.5% | **Free rider was credited the same score as each honest worker (247)** |
| Bundle verification, 1 poisoner | **17.7%** | **Every bundle rejected; nobody learns or earns** |
| Unverified averaging, all honest | 85.2% | Simple baseline, no checks |
| Unverified averaging, 1 poisoner | 61.8% | Model badly damaged |

Verification is clearly worth having when someone misbehaves. But H5 is
refuted: per-update verification captured only part of the available learning
(82.3% against 85.2%), because of the resolution limit in E6. Bundling recovers
the learning and loses attribution: it credits free riders and lets one poisoner
stop everyone.

### E2. Do worthless updates get through? (400 fresh-batch trials each)

| Update | Accepted at 1/1,024 | Accepted at 1/16 (limit 25) | True accuracy change |
| --- | ---: | ---: | ---: |
| All zeros | 0 | 0 | 0 |
| Replay of an already accepted update | 0 | 0 | 0 |
| Correct training procedure on wrong labels | 0 | 0 | −76.4% |
| Sparse tiny noise | 0 | 3 | +0.01% |
| Dense small noise | 0 | 11 | −0.04% |
| Dense large noise | 0 | 0 | −25.3% |

The true accuracy change is the mean over the first 5 trials of each row.
The weaker 1/16 level was included only to check that the test behaves as
calculated. Zero acceptances in 400 trials do not prove the rate is zero; the
1-in-1,024 limit is the claim, and it follows from the test itself.

### E3. Gaming the evaluator with no training data

The attacker has **no data**. It submits random changes and keeps those whose
published score went up.

| Evaluation design | Result on that design | True accuracy change | Same update on a fresh batch |
| --- | --- | ---: | --- |
| Hidden set, reused, scores published (400 queries) | 11 wins, 0 losses: **accepted** | −0.41% | 1 win, 12 losses: rejected |
| Public fixed set (4,000 offline tries) | 10 wins, 1 loss: not accepted (just short) | −0.24% | 10 wins, 15 losses: rejected |
| Fresh batch per submission (400 queries) | Attacker believed +6; final 9 wins, 10 losses: rejected | −0.24% | n/a |

A reused evaluation set leaks through its scores. With this small model the
leak is slow, but it produced an accepted update that made the model worse. My
public-set attacker fell just short of the threshold in this run; I report that
as it is.

### E4. Splitting one update across six identities (30 repeats)

| Reward rule | One submission | Six pieces |
| --- | ---: | ---: |
| Proportional to net wins | 947.4 | 948.8 |
| Fixed reward per accepted update | 1.0 | **6.0** |

Proportional scoring makes splitting pointless. A fixed reward per acceptance
would be exploitable and must not be used.

### E5. A backdoor that passes (counterexample)

Starting from a 62.5% model, a worker trains on its real data plus copies
stamped with an out-of-range "trigger" and labelled with a class of its choice.

| Update | Accepted | Score | Clean accuracy change | Triggered inputs sent to the attacker's class |
| --- | ---: | ---: | ---: | ---: |
| Honest | 30 / 30 | 243 | +15.8% | 0.02% |
| **Backdoored** | **30 / 30** | 155 | +10.2% | **61.1%** |
| Trigger only, no learning | 0 / 30 | 0 | −0.2% | 3.9% |

H6 is refuted. Evaluation on clean data cannot see behaviour that only appears
on inputs the evaluator never draws. The backdoor cost the attacker about a
third of its score, so it is credited less, but it is still credited.

### E6. The resolution limit

The same honest procedure applied to stronger and stronger starting models
gives smaller and smaller true gains. Acceptance rate by evaluation batch size
(100 trials per cell):

| True gain | 250 | 500 | 1,000 | 2,000 | 4,000 | 8,000 | Predicted size for 50% |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +24.3% | 100% | 100% | 100% | 100% | 100% | 100% | 44 |
| +16.1% | 95% | 100% | 100% | 100% | 100% | 100% | 90 |
| +10.4% | 72% | 100% | 100% | 100% | 100% | 100% | 169 |
| +5.6% | 30% | 81% | 100% | 100% | 100% | 100% | 312 |
| +2.5% | 5% | 12% | 40% | 81% | 100% | 100% | 1,181 |

The batch needed grows roughly as (share of examples that change) ÷ (true
gain)², times about 9.5 for the 1-in-1,024 level. **Halving the improvement
you want to certify roughly quadruples the evaluation work.** A worker whose
honest update is worth +2.5% is rejected 60% of the time at 1,000 examples.

### E7. Cost

| Quantity | Measured |
| --- | ---: |
| Worker training (3,000-example shard) | 16,800 example passes, 104.1 ms |
| Full re-execution | Same as training |
| Verification (1,500 fresh examples, two models) | 3,000 passes, 20.3 ms including data generation |
| **Verification ÷ training** | **17.9% by passes, 19.5% by time** |
| Same batch if the shard were 4×, 16×, 64× larger | 4.5%, 1.1%, 0.28% |
| Second validator's audit ÷ first evaluator's work | 30.5% by time (20.8% by multiplications) |
| Update size | 576 bytes |

Verification cost does not depend on how much training went into an update.
It depends on the batch size, and E6 says the batch size is set by how small a
gain must be certified. In this toy setting the ratio is **not** impressive:
certifying the +2.5% update reliably takes about 4,000 passes, a quarter of the
training that produced it. The ratio improves only as training effort per
update grows.

**Compared with UW-1.** A training step run exactly as prescribed on wrong
labels is reproduced bit for bit (so any exactness check, including UW-1's,
accepts it), lowers true accuracy by 76.4%, and is rejected here with 33 wins
against 1,178 losses. UW-1 answers "was this calculated correctly?" cheaply and
soundly. UW-2 answers "did this help?" at a statistical cost. They are
complements: UW-1's check fits the *evaluation* step of UW-2.

### E8. If the attacker supplies some of the evaluation examples

The attacker learns nothing. It plants trigger examples in the evaluation
batch and submits a trigger-only update.

| Attacker's share of the batch | Accepted | Mean net wins | True accuracy change |
| ---: | ---: | ---: | ---: |
| 0–5% | 0 / 30 | about +1 | +0.05% |
| 10% | 0 / 30 | +24.6 | −8.7% |
| 20% | **30 / 30** | +185.3 | **−8.7%** |

With a fifth of the evaluation data, an attacker is credited every time for
damaging the model. This crude attack needed a large share; a subtler one that
combines planted examples with real learning would need less.

## 6. What is established, and what limits were found

Supported by this evidence, under the stated trust assumptions:

- Zero, noise, replayed and wrong-label updates earned nothing (E2). Copying
  another worker's revealed update is refused by the commitment check, which is
  covered by a unit test and not by a statistical experiment.
- Splitting across identities earned nothing extra under proportional scoring.
- Fresh batches defeated a query attack that beat a reused evaluation set.
- Poisoned updates were blocked where unverified averaging was badly damaged.
- Verification cost is independent of training effort and of training method.

Limits, in order of seriousness:

1. **Fresh labelled data needs a source nobody can corrupt or predict
   (fundamental).** Usefulness cannot be measured without examples the worker
   could not train on. Someone must produce them after commitments close, or
   hold them secretly before. Here that is a trusted oracle. E8 shows what a
   partly dishonest source costs. Possible directions, all unproven: data that
   only exists later (future public data), many independent data committers
   with stake, or tasks whose examples can be generated and labelled by
   verifiable computation.
2. **Outcome checks cannot see hidden behaviour (fundamental for this
   design).** E5 is a concrete counterexample. Measured improvement on a
   distribution says nothing about inputs outside it.
3. **Small improvements cannot be certified cheaply (statistical law).** The
   evaluation needed grows with the inverse square of the gain. Mature models
   improve in small steps, so per-contribution rewards become expensive
   exactly when the model is good.
4. **Attribution against robustness.** Verifying each update gives fair
   credit but rejects small honest work. Verifying the bundle learns more and
   costs less, but credits free riders and lets one poisoner veto the round.
   Leave-one-out attribution would need one more evaluation per worker and
   meets limit 3 again.
5. **The cost advantage is conditional.** At this scale verification costs
   18–25% of training. It becomes "much cheaper" only when each update
   embodies far more training than the evaluation batch.

Approaches that failed along the way: the plain perceptron stalled at about
59% under label noise and was replaced by an averaged version; my first attack
implementations were too weak to defeat even the baselines and were rewritten;
an unverified *sum* of updates collapsed for reasons unrelated to security and
was replaced by averaging as the fair baseline.

Remaining uncertainties: one synthetic linear task; one machine; pure Python;
no real dataset; no authenticated identities; no economic model for fees
against the 1-in-1,024 false-acceptance rate; attackers limited to the
strategies listed; no cap on submissions per round and no rollback of an
accepted update. Published work on adaptive holdout reuse, backdoor
poisoning, robust aggregation and data valuation is relevant and was not
re-verified in this session.

## 7. Can this work in a decentralized setting?

Not as it stands. The arithmetic of evaluation is easy to decentralize: it is
deterministic, replayable and cheap to audit. The hard parts are not
arithmetic. They are where fresh labelled data comes from, who draws the
randomness, and how to handle behaviour evaluation cannot see. Until the data
source question has a credible answer, this design is a useful component for a
network with a **trusted or committee-run evaluator**, not a trustless
protocol. It does not provide consensus security.

## 8. Next experiment

**UW-3: remove the trusted data oracle, and measure what that costs.**
Replace the oracle with K independent data committers who each commit a
hidden evaluation shard before the round and reveal it after updates are
committed. Fix in advance:

- Evaluation batches are drawn across committers by the beacon.
- A fraction f of committers collude with a worker and share their shard.
- Measure, for f from 0 to 50% and K from 4 to 32: the attacker's acceptance
  rate and score with no learning, the damage to true accuracy, and the effect
  of two defences: discarding each worker's best-scoring committers, and
  requiring improvement on a majority of committers separately.
- **GO** if, for some K ≤ 16 and f ≤ 25%, the no-learning attacker's acceptance
  stays at or below 1 in 1,024 per submission while honest updates worth +5%
  are still accepted at least 80% of the time, at no more than twice today's
  evaluation cost. **NO-GO** otherwise, which would mean a trusted evaluator is
  unavoidable for this family of designs.

A second, independent step is to repeat E1–E6 on a real, permissively licensed
dataset with a provenance record, after a safety review of that data.

## 9. Reproduce

```powershell
python -m verunai.uw2.experiments --output my-uw2-results.json   # about 6 minutes
python -m verunai.uw2.experiments --quick --output my-quick.json  # about 5 seconds
python -m unittest tests.test_uw2 -v
```

All numbers except the timings in E7 are identical on every run and platform:
data comes from hash streams, training is integer arithmetic, and the beacons
in the experiments are recorded values. A live round draws its beacon from the
system's secure random generator. Reference environment: Windows 11 build
26300, CPython 3.14.5, Intel family 6 model 183 with 28 logical CPUs, single
process, no GPU. Energy was not measured.
