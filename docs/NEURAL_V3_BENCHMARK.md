# Canonical neural-v3 work-factor benchmark

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
- **SHA-256** measures hashing pre-encoded block payload bytes. This control
  measures hash throughput only.
- **Block validation** initializes a fresh chain and validates its first
  winning block. **Replay** imports already parsed exports at half and full
  fixture height. It includes parsing block objects and checking their state
  transitions. Disk reads, JSON decoding, transport, and signature verification
  are outside this workload.

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
| Neural computation | 3.39 ms | 3.03–3.90 ms | 51,901 |
| Candidate generation | 3.91 ms | 3.76–3.99 ms | 51,901 |
| SHA-256 on pre-encoded bytes | 0.908 µs | 0.901–0.996 µs | 97 |
| Validate first block | 4.89 ms | 3.75–6.44 ms | 47,277 |
| Replay 4 blocks (2,147 canonical JSON bytes) | 12.25 ms | 12.00–12.54 ms | 55,920 |
| Replay 8 blocks (4,170 canonical JSON bytes) | 24.41 ms | 23.59–24.86 ms | 56,846 |

The median candidate rate was about 256 attempts per second. Replay time
roughly doubled between these two small fixtures. These observations do not
establish how larger chains, transaction-heavy blocks, or networked nodes scale.

## Protocol and safety limits

The validator checks that the submitted result matches the canonical update
and that the block hash meets the target. Agreement on the output establishes
neither a minimum amount of computation per attempt nor the usefulness of
the toy training task. Verification recomputes the update, so the verifier's
cost remains relevant to resource exhaustion. See
[v0.6 security findings](SECURITY_FINDINGS_V06.md).

This benchmark introduces no changes to protocol rules, training data, rewards,
peer exposure, or model release practices. It uses the existing embedded corpus
and performs all work locally. The measurements support research review and
do not establish secure Proof of Useful Work.
