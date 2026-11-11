# Canonical neural-v3 implementation benchmark

Run from the repository root with Python 3.10+ and the dependencies in
`pyproject.toml` installed.

```powershell
python -m verunai.ledger_benchmark --attempts 150 --repeats 5 --blocks 8
python scripts/check_repository_layout.py
python scripts/check_project_standards.py
python -m unittest discover -s tests -v
```

On the measurement host, the Windows Python alias was unavailable in the
sandbox. The benchmark used the interpreter directly.

```powershell
$verunaiPython = "$env:USERPROFILE\AppData\Local\Python\pythoncore-3.14-64\python.exe"
& $verunaiPython -B -m verunai.ledger_benchmark --attempts 150 --repeats 5 --blocks 8
```

The [reference JSON](../evidence/neural_v3_canonical_benchmark.json) contains
the raw samples. To save a new run, pipe the command output to
`Set-Content -Encoding utf8 <output-path>`.

## What is measured

The benchmark mines a deterministic difficulty-1 chain of empty TEST blocks
using the existing v3 miner. A fresh validator accepts the first winning
block, and a separate replay validates the exported chain. Fixture setup is
outside the measurements. The fixture needs no signing keys, networking, or
external data.

- **Neural computation** includes selecting the batch, calculating the gradient
  and next weights, and hashing the gradient. It uses the weights at the
  fixture tip and tries the same sequence of nonces as the candidate workload.
- **Candidate generation** additionally commits the new weights and builds and
  hashes a block candidate. Throughput counts all attempts.
- **Block validation** includes fresh chain construction for each sample.
  The accepted case uses the original winning block. The early rejection
  case replaces its gradient commitment with malformed text. The late
  rejection case keeps the winning block intact and alters one weight in the
  local verifier fixture to simulate disagreement about the expected result.
  The real validator reaches the neural recomputation in that last case.
  This measures local rejection cost without constructing or submitting a
  target-valid block with falsified commitments.
- **Replay** imports already parsed exports at half and full
  fixture height. It includes parsing block objects and checking their state
  transitions. Disk reads, JSON decoding, transport, and signature verification
  are outside this workload.

The standalone SHA-256 measurement was removed. Repeatedly hashing the same
pre-encoded payload measures a primitive in isolation. Candidate generation
includes payload construction and model computation, so comparing those rates
does not estimate an alternative miner's throughput or a verifier cost ratio.

Each metric gets one warm-up, repeated wall-clock samples, and a separate
memory pass. JSON output includes all samples, median, range, and median
absolute deviation. For batched operations, timing is the average per
operation in each batch. Memory is the peak Python allocation traced during
one complete sample. It excludes the prebuilt fixture and does not measure
process resident memory, native allocations, or GPU memory.

## Reference run

Windows 11 build 26300, Python 3.14.5, Intel Family 6 Model 183 with 28
logical CPUs. The benchmark used one process and the canonical Python CPU
backend. The host had an RTX 5070. No GPU work or power measurements were
performed. This is one local observation with uncontrolled background load.

| Workload | Median | Sample range | Peak traced bytes |
| --- | ---: | ---: | ---: |
| Neural computation | 1.915 ms | 1.907–1.922 ms | 51,901 |
| Candidate generation | 1.934 ms | 1.911–1.973 ms | 51,901 |
| Accept first block | 1.796 ms | 1.743–2.056 ms | 47,285 |
| Reject malformed commitment | 0.0031 ms | 0.0029–0.0061 ms | 4,118 |
| Reject neural mismatch | 1.916 ms | 1.902–2.007 ms | 47,246 |
| Replay 4 blocks (2,147 canonical JSON bytes) | 7.335 ms | 7.096–7.619 ms | 55,928 |
| Replay 8 blocks (4,170 canonical JSON bytes) | 15.592 ms | 15.270–15.851 ms | 56,854 |

The median candidate rate was about 517 attempts per second. Training and
candidate samples each contained 150 operations. Validation and replay each
used one operation per sample, with five samples per workload. Late rejection
cost about as much as acceptance. The early rejection timings are on a
microsecond scale and include setup, so they are sensitive to harness overhead.
The observations do not establish how larger chains, transaction-heavy blocks,
or networked nodes scale. They also do not isolate the performance effect of
reusing the model digest. The regression test verifies the eliminated call.

## Protocol and safety limits

**H1 — Result equivalence and minimum work.** The training step is a linear
model with a squared-error objective. Its gradient can be expressed as
batch-dependent terms combined with the current weights. Exact integer
arithmetic permits regrouping those operations while preserving the gradient,
quantized update, and commitments. The owner relayed Claude's approximately
17× result for an equivalent calculation in a controlled experiment. The
experiment's raw data and procedure were unavailable for this report. That
figure describes the isolated calculation and is unverified here. It cannot
be used as a v3 candidate-throughput multiplier. A commitment authenticates
the output against the reference calculation. It contains no record of the
operations used to produce that output or the time and resources they took.
The numbers above measure the canonical implementation only.

**M1 — Cost of rejecting invalid work.** The validator recomputes the update
for commitments that reach the neural check. The local late-rejection
measurement isolates that path. It does not measure submission cost, network
effects, or exploitability. The underlying verification-cost risk remains
open. See
[v0.6 security findings](SECURITY_FINDINGS_V06.md).

This benchmark introduces no changes to protocol rules, training data, rewards,
peer exposure, or model release practices. It uses the existing embedded corpus
and performs all work locally. The measurements support research review and
do not establish secure Proof of Useful Work.
