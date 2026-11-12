"""UW-2 experiments: honest learning, baselines and attacks on the protocol itself.

Run all experiments and write raw evidence:
    python -m verunai.uw2.experiments --output evidence/uw2_results.json

Every number except wall-clock timings is deterministic: data comes from
SHAKE-256 streams, training is integer arithmetic, and beacons are *recorded*
values derived from labels. A live protocol must draw beacons from a CSPRNG
after commitments close; ``protocol.Round`` does that by default.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter

from . import audit
from .data import CLASSES, FEATURES, Oracle, overlap
from .model import (Weights, accuracy_count, add, decode, digest, encode, predict, subtract,
                    train_averaged, zero_weights)
from .protocol import Round, paired_counts, replay, submit
from .stats import DEFAULT_ALPHA, improved
from .workers import (HONEST_STEPS, backdoor_update, honest_training_forward_passes,
                      honest_update, label_flip_update, mean_update, noise_update,
                      split_by_features, trigger_only_update, with_trigger, zero_update)

LOOSE_ALPHA = (1, 16)  # deliberately weak level used only to calibrate the test empirically


@dataclass(frozen=True)
class Config:
    """Experiment sizes. ``quick()`` gives a small configuration for CI tests."""

    seed: str = "uw2-evidence-v1"
    workers: int = 4
    shard: int = 3000
    batch: int = 1500
    test: int = 20000
    rounds: int = 5
    trajectories: int = 5
    null_trials: int = 400
    power_trials: int = 100
    power_batches: tuple[int, ...] = (250, 500, 1000, 2000, 4000, 8000)
    repeats: int = 30

    @classmethod
    def quick(cls) -> "Config":
        return cls(seed="uw2-quick", shard=600, batch=300, test=3000, rounds=3, trajectories=2, null_trials=20,
                   power_trials=10, power_batches=(100, 400), repeats=4)


def recorded_beacon(*parts: object) -> bytes:
    """Return a reproducible stand-in for a post-commitment random beacon."""
    return sha256(("UW2/recorded-beacon/" + "/".join(map(str, parts))).encode()).digest()


def _rate(weights: Weights, test) -> float:
    return accuracy_count(weights, *test) / len(test[0])


def _mean(values) -> float:
    return sum(values) / len(values)


def _scale(weights: Weights) -> int:
    return max((abs(v) for row in weights for v in row), default=0)


def _score_once(oracle: Oracle, base: Weights, delta: Weights, batch: int, *tag: object,
                alpha=DEFAULT_ALPHA) -> tuple[int, int, bool]:
    """Score one update against ``base`` on a fresh recorded batch."""
    data = oracle.evaluation_batch(recorded_beacon(*tag), b"direct", batch)
    wins, losses = paired_counts(base, add(base, delta), data)
    return wins, losses, improved(wins, losses, alpha)


def _base_from(shard, examples: int) -> Weights:
    """Return a model trained on the first ``examples`` of a shard (a weaker or stronger start)."""
    return train_averaged(zero_weights(), shard[0][:examples], shard[1][:examples], 2, 16)


def _hardest_target(weights: Weights, test) -> int:
    """Return the class an honest model predicts least often on triggered inputs."""
    counts = [0] * CLASSES
    for x in test[0][:3000]:
        counts[predict(weights, with_trigger(x))] += 1
    return counts.index(min(counts))


def _attack_success(weights: Weights, test, target: int) -> float:
    victims = [with_trigger(x) for x, y in zip(*test) if y != target][:5000]
    return sum(predict(weights, x) == target for x in victims) / len(victims)


# --------------------------------------------------------------------------- E1
def _run_rounds(cfg: Config, oracle: Oracle, shards, test, strategies, label: str, mode: str) -> dict:
    """Run rounds in one mode: per_update, bundle, or average_unverified."""
    weights = zero_weights()
    history, scores, eval_batches = [], {}, []
    trained = scored = 0
    for number in range(cfg.rounds):
        round_ = Round(oracle, weights, number, cfg.batch,
                       beacon_source=lambda n=number: recorded_beacon(label, n))
        reveals = {}
        for index, (kind, strategy) in enumerate(strategies):
            delta = strategy(weights, shards[index])
            trained += honest_training_forward_passes(cfg.shard) if kind == "honest" else 0
            if delta is not None:
                name = f"w{index}-{kind}"
                reveals[name] = submit(round_, name, delta,
                                       sha256(f"{label}{number}{index}".encode()).digest())
        beacon = round_.close_commitments()
        for name, (update, salt) in reveals.items():
            round_.reveal(name, update, salt)
        if mode == "per_update":
            before = weights
            settlements = round_.settle()
            weights = round_.weights
            if not replay(round_.record(), oracle, before, {n: u for n, (u, _) in reveals.items()}):
                raise RuntimeError("round replay disagreed with the settlement")
            for item in settlements:
                scores[item.worker] = scores.get(item.worker, 0) + item.score
                if item.status in ("accepted", "rejected"):
                    scored += 1
                    eval_batches.append(oracle.evaluation_batch(
                        beacon, bytes.fromhex(item.commitment), cfg.batch))
            outcome = [[s.worker, s.status, s.wins, s.losses] for s in settlements]
        else:
            outcome = []
            if reveals:
                bundle = mean_update([decode(update) for update, _ in reveals.values()])
                candidate = add(weights, bundle)
                if mode == "bundle":  # one test for the averaged update; equal split of its score
                    batch = oracle.evaluation_batch(beacon, b"bundle", cfg.batch)
                    eval_batches.append(batch)
                    scored += 1
                    wins, losses = paired_counts(weights, candidate, batch)
                    accepted = improved(wins, losses)
                    outcome = [["bundle", "accepted" if accepted else "rejected", wins, losses]]
                    if accepted:
                        weights = candidate
                        for name in reveals:
                            scores[name] = scores.get(name, 0) + (wins - losses) // len(reveals)
                else:  # baseline: apply the average with no check
                    weights = candidate
                    outcome = [["bundle", "applied_unverified", 0, 0]]
        history.append({"round": number, "true_accuracy": _rate(weights, test), "updates": outcome})
    return {"history": history, "final_true_accuracy": history[-1]["true_accuracy"],
            "scores": dict(sorted(scores.items())), "honest_training_forward_passes": trained,
            "verification_forward_passes": 2 * cfg.batch * scored, "scored_updates": scored,
            "evaluation_overlap_with_training_or_test":
                overlap(*shards, test, *eval_batches) if eval_batches else None,
            "final_model": digest(weights)}


def experiment_collaboration(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E1: does verified collaboration learn, and what does each design cost in attribution?"""
    honest = ("honest", lambda w, shard: honest_update(w, shard))
    poisoner = ("poisoner", lambda w, shard: label_flip_update(w, shard))
    free_rider = ("freerider", lambda w, shard: zero_update())
    all_honest = [honest] * cfg.workers
    with_poisoner = [honest] * (cfg.workers - 1) + [poisoner]
    with_free_rider = [honest] * (cfg.workers - 1) + [free_rider]
    pooled = (sum((s[0] for s in shards), ()), sum((s[1] for s in shards), ()))

    def run(strategies, label: str, mode: str) -> dict:
        """Repeat one condition with independent recorded beacons; keep the first run in full."""
        runs = [_run_rounds(cfg, oracle, shards, test, strategies, f"{label}/{t}", mode)
                for t in range(cfg.trajectories)]
        finals = [r["final_true_accuracy"] for r in runs]
        return {**runs[0], "final_true_accuracy_by_trajectory": finals,
                "mean_final_true_accuracy": _mean(finals),
                "scores_by_trajectory": [r["scores"] for r in runs]}

    return {
        "chance_accuracy": _rate(zero_weights(), test),
        "teacher_accuracy_ceiling": _rate(oracle._teacher, test),
        "centralized_pooled_reference": _rate(train_averaged(zero_weights(), *pooled, 2, 16), test),
        "single_worker_alone": _rate(add(zero_weights(), honest_update(zero_weights(), shards[0])), test),
        "per_update_honest": run(all_honest, "E1a", "per_update"),
        "per_update_with_poisoner": run(with_poisoner, "E1b", "per_update"),
        "bundle_honest": run(all_honest, "E1c", "bundle"),
        "bundle_with_free_rider": run(with_free_rider, "E1d", "bundle"),
        "bundle_with_poisoner": run(with_poisoner, "E1e", "bundle"),
        "unverified_average_honest": run(all_honest, "E1f", "average_unverified"),
        "unverified_average_with_poisoner": run(with_poisoner, "E1g", "average_unverified"),
    }


# --------------------------------------------------------------------------- E2
def experiment_null_attacks(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E2: how often do worthless or harmful updates get accepted?"""
    first = honest_update(zero_weights(), shards[0])
    base = add(zero_weights(), first)
    fixed = {"zero": zero_update(), "replay_accepted_update": first,
             "label_flip_correct_procedure": label_flip_update(base, shards[1])}
    scale = _scale(base)
    noise = {"noise_sparse_tiny": (max(1, scale // 400), 16),
             "noise_dense_small": (max(1, scale // 100), 256),
             "noise_dense_large": (max(1, scale // 2), 256)}
    report = {"base_true_accuracy": _rate(base, test), "trials_per_strategy": cfg.null_trials}
    for name in (*fixed, *noise):
        strict = loose = 0
        true_changes = []
        for trial in range(cfg.null_trials):
            delta = fixed[name] if name in fixed else noise_update(f"{name}/{trial}".encode(), *noise[name])
            wins, losses, accepted = _score_once(oracle, base, delta, cfg.batch, "E2", name, trial)
            strict += accepted
            loose += improved(wins, losses, LOOSE_ALPHA)
            if trial < 5:
                true_changes.append(_rate(add(base, delta), test) - report["base_true_accuracy"])
        report[name] = {"accepted_at_1_in_1024": strict, "accepted_at_1_in_16": loose,
                        "mean_true_accuracy_change_first_5": _mean(true_changes)}
    report["expected_upper_limits"] = {"at_1_in_1024": cfg.null_trials / 1024,
                                       "at_1_in_16": cfg.null_trials / 16}
    return report


# --------------------------------------------------------------------------- E3
def _climb(queries: int, magnitude: int, label: str, score) -> tuple[Weights, int]:
    """Hill-climb with random probes, keeping a probe only when its published score improves."""
    current, best = zero_weights(), 0
    for q in range(queries):
        probe = noise_update(f"E3/{label}/{q}".encode(), magnitude, 24)
        candidate = tuple(tuple(a + b for a, b in zip(cr, pr)) for cr, pr in zip(current, probe))
        wins, losses = score(q, candidate)
        if wins - losses > best:
            current, best = candidate, wins - losses
    return current, best


def experiment_evaluator_overfitting(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E3: public and reused evaluation sets versus fresh post-commitment batches."""
    pooled = (sum((s[0] for s in shards), ()), sum((s[1] for s in shards), ()))
    base = train_averaged(zero_weights(), *pooled, 2, 16)
    base_rate = _rate(base, test)
    size = max(100, cfg.batch // 4)
    magnitude = max(1, _scale(base) // 40)
    queries = max(40, cfg.null_trials)

    def summarise(delta: Weights, held, tag: str) -> dict:
        wins, losses = paired_counts(base, add(base, delta), held)
        fresh = _score_once(oracle, base, delta, cfg.batch, "E3", tag, "fresh")
        return {"set_size": len(held[0]), "measured_wins": wins, "measured_losses": losses,
                "accepted_on_that_set": improved(wins, losses),
                "true_accuracy_change": _rate(add(base, delta), test) - base_rate,
                "same_update_on_fresh_batch": {"wins": fresh[0], "losses": fresh[1], "accepted": fresh[2]}}

    # Baseline B0: the evaluation set is public. The attacker has no training data at
    # all and tunes directly against the set, offline, as often as it likes.
    public = oracle.evaluation_batch(recorded_beacon("E3", "public"), b"fixed", size)
    tuned, _ = _climb(queries * 10, magnitude, "public",
                      lambda q, cand: paired_counts(base, add(base, cand), public))
    # Baseline B1: the set is hidden but reused, and each submission's score is published.
    hidden = oracle.evaluation_batch(recorded_beacon("E3", "hidden"), b"fixed", size)
    reused, _ = _climb(queries, magnitude, "hidden",
                       lambda q, cand: paired_counts(base, add(base, cand), hidden))
    # The same query attack when every submission is scored on its own fresh batch.
    fresh_delta, believed = _climb(
        queries, magnitude, "fresh",
        lambda q, cand: _score_once(oracle, base, cand, size, "E3", "fq", q)[:2])
    final = _score_once(oracle, base, fresh_delta, cfg.batch, "E3", "fresh-final")
    return {"base_true_accuracy": base_rate, "attacker_training_examples": 0,
            "public_fixed_set": {"offline_queries": queries * 10, **summarise(tuned, public, "public")},
            "hidden_reused_set": {"queries": queries, **summarise(reused, hidden, "hidden")},
            "fresh_batch_per_submission": {
                "queries": queries, "attacker_believed_net_wins": believed,
                "final_submission": {"wins": final[0], "losses": final[1], "accepted": final[2]},
                "true_accuracy_change": _rate(add(base, fresh_delta), test) - base_rate}}


# --------------------------------------------------------------------------- E4
def experiment_sybil_splitting(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E4: does splitting one update across identities earn more?"""
    delta = honest_update(zero_weights(), shards[0])
    parts = 6
    pieces = split_by_features(delta, parts)
    whole_scores, split_scores, split_accepts, whole_accepts = [], [], [], []
    for repeat in range(cfg.repeats):
        wins, losses, accepted = _score_once(oracle, zero_weights(), delta, cfg.batch, "E4", "whole", repeat)
        whole_scores.append(wins - losses if accepted else 0)
        whole_accepts.append(int(accepted))
        weights, total, count = zero_weights(), 0, 0
        for index, piece in enumerate(pieces):
            wins, losses, accepted = _score_once(oracle, weights, piece, cfg.batch, "E4", "piece", repeat, index)
            if accepted:
                weights = add(weights, piece)
                total += wins - losses
                count += 1
        split_scores.append(total)
        split_accepts.append(count)
    return {"pieces": parts, "repeats": cfg.repeats,
            "proportional_rule": {"whole_mean_score": _mean(whole_scores),
                                  "split_mean_total_score": _mean(split_scores)},
            "fixed_reward_per_acceptance_rule": {"whole_mean_rewards": _mean(whole_accepts),
                                                 "split_mean_rewards": _mean(split_accepts)},
            "raw": {"whole_scores": whole_scores, "split_scores": split_scores,
                    "split_accepted_pieces": split_accepts}}


# --------------------------------------------------------------------------- E5
def experiment_backdoor(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E5: can an update that passes the improvement test carry a hidden behaviour?"""
    base = _base_from(shards[0], max(60, cfg.shard // 10))
    xs, ys = shards[1]
    cut = len(xs) * 4 // 5
    honest = honest_update(base, shards[1])
    target = _hardest_target(add(base, honest) if honest is not None else base, test)
    best, best_count = None, -1
    for step in HONEST_STEPS:  # the attacker also keeps its best candidate on clean validation data
        delta = backdoor_update(base, (xs[:cut], ys[:cut]), cut // 4, target, 2, step)
        count = accuracy_count(add(base, delta), xs[cut:], ys[cut:])
        if count > best_count:
            best, best_count = delta, count
    candidates = {"honest": honest, "backdoored": best,
                  "trigger_only": trigger_only_update(_scale(base) // 4 + 8, target)}
    report = {"base_true_accuracy": _rate(base, test), "trigger_target_class": target,
              "attack_success_rate_before": _attack_success(base, test, target)}
    for name, delta in candidates.items():
        if delta is None:
            report[name] = {"submitted": False}
            continue
        accepted, nets = 0, []
        for repeat in range(cfg.repeats):
            wins, losses, ok = _score_once(oracle, base, delta, cfg.batch, "E5", name, repeat)
            accepted += ok
            nets.append(wins - losses)
        after = add(base, delta)
        report[name] = {"submitted": True, "accepted": accepted, "of": cfg.repeats,
                        "mean_net_wins": _mean(nets),
                        "clean_true_accuracy_change": _rate(after, test) - report["base_true_accuracy"],
                        "attack_success_rate_after": _attack_success(after, test, target)}
    return report


# --------------------------------------------------------------------------- E6
def experiment_resolution(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E6: how many fresh examples are needed to certify a given true improvement?"""
    big = oracle.test_set(5 * cfg.test, b"resolution")
    rows = []
    for examples in (cfg.shard // 20, cfg.shard // 10, cfg.shard // 5, cfg.shard * 2 // 5, cfg.shard * 4 // 5):
        base = _base_from(shards[0], examples)
        delta = honest_update(base, shards[1])
        if delta is None:
            rows.append({"base_training_examples": examples, "submitted": False})
            continue
        wins, losses = paired_counts(base, add(base, delta), big)
        gain = (wins - losses) / len(big[0])
        discordant = (wins + losses) / len(big[0])
        power = {str(batch): sum(_score_once(oracle, base, delta, batch, "E6", examples, batch, t)[2]
                                 for t in range(cfg.power_trials)) / cfg.power_trials
                 for batch in cfg.power_batches}
        rows.append({"base_training_examples": examples, "submitted": True,
                     "base_true_accuracy": _rate(base, big), "true_gain": gain,
                     "discordant_rate": discordant, "acceptance_rate_by_batch": power,
                     "normal_approximation_batch_for_half_power":
                         None if gain <= 0 else round(3.09 ** 2 * discordant / gain ** 2)})
    return {"trials_per_cell": cfg.power_trials, "alpha": list(DEFAULT_ALPHA),
            "ground_truth_examples": len(big[0]), "updates": rows}


# --------------------------------------------------------------------------- E7
def _median_ms(operation, repeats: int = 5) -> float:
    operation()
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        operation()
        samples.append((perf_counter() - start) * 1000)
    return median(samples)


def experiment_costs(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E7: measured cost of training, re-execution, evaluation and audited evaluation."""
    base = zero_weights()
    delta = honest_update(base, shards[0])
    candidate = add(base, delta)
    beacon = recorded_beacon("E7")
    batch = oracle.evaluation_batch(beacon, b"cost", cfg.batch)
    claimed_old, claimed_new = audit.scores(base, batch[0]), audit.scores(candidate, batch[0])
    challenge = audit.draw_challenge()
    if not (audit.check_scores(base, batch[0], claimed_old, challenge) and
            audit.check_scores(candidate, batch[0], claimed_new, challenge)):
        raise RuntimeError("honest evaluation claim failed its audit")
    forged = (tuple(v + (1 if i == 0 else 0) for i, v in enumerate(claimed_new[0])),) + claimed_new[1:]
    timing = {
        "worker_training_ms": _median_ms(lambda: honest_update(base, shards[0])),
        "evaluation_data_generation_ms": _median_ms(lambda: oracle.evaluation_batch(beacon, b"cost", cfg.batch)),
        "verification_two_model_evaluation_ms": _median_ms(lambda: paired_counts(base, candidate, batch)),
        "first_evaluator_score_matrices_ms": _median_ms(
            lambda: (audit.scores(base, batch[0]), audit.scores(candidate, batch[0]))),
        "second_validator_audit_ms": _median_ms(
            lambda: (audit.check_scores(base, batch[0], claimed_old, challenge),
                     audit.check_scores(candidate, batch[0], claimed_new, challenge),
                     audit.predictions(claimed_old), audit.predictions(claimed_new))),
    }
    timing["verification_including_data_ms"] = (timing["evaluation_data_generation_ms"] +
                                                timing["verification_two_model_evaluation_ms"])
    passes = honest_training_forward_passes(cfg.shard)
    flipped = label_flip_update(candidate, shards[1])
    wins, losses, accepted = _score_once(oracle, candidate, flipped, cfg.batch, "E7", "flip")
    return {
        "forward_passes": {
            "worker_training": passes, "full_reexecution": passes, "verification": 2 * cfg.batch,
            "verification_over_training": 2 * cfg.batch / passes,
            "verification_over_training_if_shard_were": {
                str(size): 2 * cfg.batch / honest_training_forward_passes(size)
                for size in (cfg.shard, 4 * cfg.shard, 16 * cfg.shard, 64 * cfg.shard)}},
        "multiplications_per_example": {"score_matrix": FEATURES * CLASSES,
                                        "audited_check": FEATURES + CLASSES},
        "timing_ms": timing,
        "timing_ratios": {
            "verification_including_data_over_training":
                timing["verification_including_data_ms"] / timing["worker_training_ms"],
            "second_validator_over_first_evaluator":
                timing["second_validator_audit_ms"] / timing["first_evaluator_score_matrices_ms"]},
        "forged_score_claim_rejected": not audit.check_scores(candidate, batch[0], forged, challenge),
        "update_bytes": len(encode(delta)),
        "correct_but_harmful_step": {
            "description": "exact training procedure run on wrong labels",
            "recomputation_matches_submission": flipped == label_flip_update(candidate, shards[1]),
            "accepted_by_improvement_test": accepted, "wins": wins, "losses": losses,
            "true_accuracy_change": _rate(add(candidate, flipped), test) - _rate(candidate, test)},
    }


# --------------------------------------------------------------------------- E8
def experiment_colluding_evaluation_data(cfg: Config, oracle: Oracle, shards, test) -> dict:
    """E8: what if the attacker supplies a fraction of the evaluation examples?"""
    base = add(zero_weights(), honest_update(zero_weights(), shards[0]))
    target = _hardest_target(base, test)
    base_rate = _rate(base, test)

    def mixed(xs, ys, planted: int):
        return (tuple(with_trigger(x) for x in xs[:planted]) + xs[planted:],
                (target,) * planted + ys[planted:])

    rows = []
    for per_thousand in (0, 10, 20, 50, 100, 200):
        planted = cfg.batch * per_thousand // 1000
        # The attacker tunes the strength on its own data, knowing its share of the batch.
        proxy = mixed(shards[-1][0][:cfg.batch], shards[-1][1][:cfg.batch], planted)
        strength, best = 1, None
        for candidate in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512):
            wins, losses = paired_counts(base, add(base, trigger_only_update(candidate, target)), proxy)
            if best is None or wins - losses > best:
                strength, best = candidate, wins - losses
        delta = trigger_only_update(strength, target)
        accepted, nets = 0, []
        for repeat in range(cfg.repeats):
            xs, ys = oracle.evaluation_batch(recorded_beacon("E8", per_thousand, repeat), b"mix", cfg.batch)
            wins, losses = paired_counts(base, add(base, delta), mixed(xs, ys, planted))
            accepted += improved(wins, losses)
            nets.append(wins - losses)
        rows.append({"attacker_share_per_thousand": per_thousand, "planted_examples": planted,
                     "chosen_strength": strength, "accepted": accepted, "of": cfg.repeats,
                     "mean_net_wins": _mean(nets),
                     "true_accuracy_change": _rate(add(base, delta), test) - base_rate})
    return {"base_true_accuracy": base_rate, "trigger_target_class": target,
            "attacker_learned_anything": False, "by_attacker_share": rows}


EXPERIMENTS = {
    "E1_collaboration": experiment_collaboration,
    "E2_null_attacks": experiment_null_attacks,
    "E3_evaluator_overfitting": experiment_evaluator_overfitting,
    "E4_sybil_splitting": experiment_sybil_splitting,
    "E5_backdoor": experiment_backdoor,
    "E6_resolution": experiment_resolution,
    "E7_costs": experiment_costs,
    "E8_colluding_evaluation_data": experiment_colluding_evaluation_data,
}


def run(cfg: Config, names: tuple[str, ...] = tuple(EXPERIMENTS)) -> dict:
    """Run the selected experiments and return a JSON-serialisable report."""
    oracle = Oracle(cfg.seed.encode())
    shards = [oracle.training_shard(i, cfg.shard) for i in range(cfg.workers)]
    test = oracle.test_set(cfg.test)
    report = {"config": asdict(cfg),
              "data": {"features": FEATURES, "classes": CLASSES,
                       "provenance": "synthetic; generated from SHAKE-256 streams in verunai/uw2/data.py",
                       "training_shards_and_test_overlap": overlap(*shards, test)}}
    for name in names:
        report[name] = EXPERIMENTS[name](cfg, oracle, shards, test)
    return report


def main() -> int:
    """Command-line entry point: run experiments and write one JSON file."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quick", action="store_true", help="small sizes for a fast smoke run")
    parser.add_argument("--experiment", action="append", choices=sorted(EXPERIMENTS))
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite {args.output}")
    report = run(Config.quick() if args.quick else Config(), tuple(args.experiment or EXPERIMENTS))
    report["environment"] = {"python": platform.python_version(), "platform": platform.platform(),
                             "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                             "note": "single process, pure-Python exact integers, no GPU"}
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
