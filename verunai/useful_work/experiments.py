"""Local statistical experiments using small synthetic matrix errors."""
from dataclasses import replace
from hashlib import sha256
from math import expm1, log1p

from .challenge import PARAMETERS, Parameters, check, sample
from .commitment import encode
from .prover import Result, canonical_prover, optimized_prover, updated
from .task import DIMENSIONS, Matrix, Task, RESIDUAL_BOUND, make_task
from .transcript import replay
from .verifier import Verifier


def perturb(matrix: Matrix, changes: dict[tuple[int, int], int]) -> Matrix:
    """Add signed deltas to selected matrix coordinates."""
    return tuple(tuple(v + changes.get((i, j), 0) for j, v in enumerate(row))
                 for i, row in enumerate(matrix))


def with_gradient(task: Task, result: Result, gradient: Matrix) -> Result:
    """Replace a claimed gradient and calculate its internally consistent update."""
    return replace(result, gradient=gradient, weights=updated(task.w, gradient, task.divisor))


def honest_trials(trials: int, dimensions: tuple[int, ...] = DIMENSIONS) -> dict:
    """Check byte parity and acceptance for both backends on distinct tasks."""
    result = {}
    for d in dimensions:
        manifest = sha256()
        for seed in range(trials):
            task = make_task(d, f"honest-{seed}", "local", "0" * 64, seed)
            packets = [encode(task, prover(task)) for prover in (canonical_prover, optimized_prover)]
            if packets[0] != packets[1] or not all(Verifier(task).submit(p).accepted for p in packets):
                raise RuntimeError(f"honest mismatch at dimension {d}, seed {seed}")
            manifest.update(sha256(packets[0]).digest())
        result[d] = dict(tasks=trials, accepted_per_backend=trials, manifest_sha256=manifest.hexdigest())
        print(f"d={d}: {trials} honest tasks passed", flush=True)
    return result


def _frequency(indices: list[int], total: int) -> dict:
    return dict(trials=total, accepted=len(indices), acceptance_rate=len(indices) / total,
                accepted_trial_indices=indices)


def _rank_one(task: Task, result: Result, trials: int) -> dict:
    report = {}
    packet = encode(task, with_gradient(task, result, perturb(result.gradient, {(0, 0): 1})))
    for bits, rounds in PARAMETERS:
        params = Parameters(bits, rounds)
        records = []
        for i in range(trials):
            transcript = Verifier(task, params).submit(packet)
            if transcript.accepted:
                records.append(dict(index=i, challenges=transcript.challenges, digest=transcript.digest))
        successes = [entry["index"] for entry in records]
        population = 2 ** (bits * task.dimension) - 1
        favorable = 2 ** (bits * (task.dimension - 1)) - 1
        p = 1.0
        for j in range(rounds):
            p *= (favorable - j) / (population - j)
        report[f"{bits},{rounds}"] = dict(
            **_frequency(successes, trials), exact_probability=p, false_acceptances=records, per_attempt_bound=2.0 ** (-bits * rounds),
            expected_success_count=trials * p,
            at_least_one_independent=-expm1(trials * log1p(-p)),
            union_bound=min(1.0, trials * 2.0 ** (-bits * rounds)))
    return report


def _repeated(task: Task, packet: bytes, trials: int) -> dict:
    # Several attempts per session; a false acceptance also closes the session.
    q = 3
    accepted = []
    attempts = 0
    for i in range(trials):
        verifier = Verifier(task, Parameters(8, 1), limit=q)
        for j in range(q):
            attempts += 1
            transcript = verifier.submit(packet)
            if transcript.accepted:
                accepted.append(dict(session=i, attempt=j + 1, challenges=transcript.challenges,
                                     digest=transcript.digest))
                break
        try:
            verifier.submit(packet)
        except ValueError:
            continue
        raise RuntimeError("repeated attempt unexpectedly admitted")
    p = (256 ** (task.dimension - 1) - 1) / (256 ** task.dimension - 1)
    return dict(sessions=trials, q=q, attempts=attempts, false_acceptances=accepted,
                acceptance_rate=len(accepted) / trials, at_least_one_independent=-expm1(q * log1p(-p)),
                union_bound=q / 256)


def _toy_grinding(trials: int) -> dict:
    # Fixed, fully enumerable rank-one toy: four possible entries, three distinct
    # kernels. Compare candidates fixed before the draw with a counterfactual
    # selection after seeing the vector. This is not a UW-1 randomness source.
    vectors = [(x, y) for x in range(4) for y in range(4) if x or y]
    rows = [(1, 0), (0, 1), (1, -1)]
    passes = [[a*x + b*y == 0 for a, b in rows] for x, y in vectors]
    predictable = [i for i in range(trials) if any(passes[i % len(vectors)])]
    fixed = [i for i in range(trials) if passes[i % len(vectors)][0]]
    return dict(population=len(vectors), exact_fixed=3/15, exact_preview=9/15,
                fixed=_frequency(fixed, trials), preview=_frequency(predictable, trials))


def _preview_comparison(task: Task, result: Result, trials: int) -> dict:
    """Contrast preview-conditioned synthetic errors with a new verifier draw."""
    params = Parameters(8, 1)
    variants = [
        with_gradient(task, result, perturb(result.gradient, delta))
        for delta in ({(0, 0): 1}, {(0, 1): 1}, {(0, 0): 1, (0, 1): -1})
    ]
    packets = [encode(task, variant) for variant in variants]
    preview_accepts, fresh_accepts = [], []
    for i in range(trials):
        preview = sample(task.dimension, params)
        r0, r1 = preview[0][:2]
        kernels = (r0 == 0, r1 == 0, r0 == r1)
        selected = kernels.index(True) if any(kernels) else 0
        if check(task, variants[selected], params, preview)[0]:
            preview_accepts.append(dict(index=i, candidate=selected, challenges=preview))
        transcript = Verifier(task, params).submit(packets[selected])
        if transcript.accepted:
            fresh_accepts.append(dict(index=i, candidate=selected, challenges=transcript.challenges,
                                      digest=transcript.digest))
    d = task.dimension
    population = 256**d - 1
    single = (256**(d - 1) - 1) / population
    # Every pair of kernels intersects in r0 = r1 = 0.
    union = (3 * 256**(d - 1) - 2 * 256**(d - 2) - 1) / population
    return dict(trials=trials, preview_probability=union, fresh_probability=single,
                preview_rate=len(preview_accepts) / trials, fresh_rate=len(fresh_accepts) / trials,
                preview_false_acceptances=preview_accepts, fresh_false_acceptances=fresh_accepts)


def adversarial(trials: int) -> dict:
    """Exercise local verifier invariants and report all synthetic false accepts."""
    d = 16
    task = make_task(d, "adversarial", "local", "0" * 64, 9)
    result = canonical_prover(task)
    honest = encode(task, result)
    rank_one = with_gradient(task, result, perturb(result.gradient, {(0, 0): 1}))
    stale = canonical_prover(make_task(d, "adversarial", "local", "0" * 64, 8))
    changed_e = perturb(result.residual, {(0, 0): 1})
    changed_g = perturb(result.gradient, {(i, 0): v for i, v in enumerate(task.x[0])})
    alternatives = {
        "A1_minus": with_gradient(task, result, perturb(result.gradient, {(0, 0): -1})),
        "A2_pair": with_gradient(task, replace(result, residual=changed_e), changed_g),
        "A3_zero": with_gradient(task, result, tuple((0,) * d for _ in range(d))),
        "A3_stale": with_gradient(task, result, stale.gradient),
        "A8_update": replace(result, weights=perturb(result.weights, {(0, 0): 1})),
    }
    frequencies = {}
    for label, alternative in alternatives.items():
        if alternative == result:
            raise RuntimeError(f"fixture is not incorrect: {label}")
        packet = encode(task, alternative)
        accepted = [i for i in range(trials) if Verifier(task).submit(packet).accepted]
        frequencies[label] = _frequency(accepted, trials)
    invalid_vectors = (((0,) * d,), ((256,) * d,), ((-1,) * d,), ((1,),))
    invalid_challenges = []
    for i in range(trials):
        try:
            check(task, result, Parameters(8, 1), invalid_vectors[i % len(invalid_vectors)])
        except ValueError:
            continue
        invalid_challenges.append(i)
    frequencies["B4_invalid_challenges"] = _frequency(invalid_challenges, trials)
    overflow = replace(result, residual=perturb(result.residual, {(0, 0): 2 * RESIDUAL_BOUND}))
    others = {
        "A7_wrong_shape": (task, honest[:-4]),
        "A7_out_of_range": (task, encode(task, overflow)),
        "A4_assignee": (make_task(d, "adversarial", "other", "0" * 64, 9), honest),
        "A5_head": (make_task(d, "adversarial", "local", "1" * 64, 9), honest),
        "A7_size": (task, honest + b"x"),
        "B6_task": (make_task(d, "other", "local", "0" * 64, 9), honest),
        "B6_payload": (task, honest[:-33] + bytes([honest[-33] ^ 1]) + honest[-32:]),
    }
    for label, (scope, packet) in others.items():
        unexpected = []
        for i in range(trials):
            try:
                Verifier(scope).submit(packet)
            except ValueError:
                continue
            unexpected.append(i)
        frequencies[label] = _frequency(unexpected, trials)
    duplicate = []
    tampered = []
    for i in range(trials):
        verifier = Verifier(task)
        t = verifier.submit(honest)
        if not t.accepted:
            raise RuntimeError("honest packet rejected")
        try:
            verifier.submit(honest)
        except ValueError:
            pass
        else:
            duplicate.append(i)
        try:
            replay(task, honest, replace(t, accepted=False), t.digest)
        except ValueError:
            pass
        else:
            tampered.append(i)
    frequencies["A9_duplicate"] = _frequency(duplicate, trials)
    frequencies["B5_tampered"] = _frequency(tampered, trials)
    return dict(default_parameters=[32, 2], categories=frequencies,
                parameter_sweep=_rank_one(task, result, trials), toy_grinding=_toy_grinding(trials),
                repeated=_repeated(task, encode(task, rank_one), trials),
                preview_comparison=_preview_comparison(task, result, trials))
