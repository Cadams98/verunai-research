# Three-node testnet harness (v0.8 phase P0)

**Status:** research measurement tool. It starts the **existing, unmodified** v0.6
node (`python -m verunai node`) as three or more separate operating-system
processes on `127.0.0.1`, waits for them to agree, and independently re-checks
what each one saved. It changes no consensus, fork-choice, networking or storage
behaviour. All rewards are fictional TEST units. Nothing listens beyond loopback.

Passing trials show that these nodes converged on one machine under the stated
conditions. They do **not** show security against hostile peers, behaviour across
real networks, or scalability.

## Run it

Python 3.10+ from the repository root, after `python -m pip install -e .`:

```powershell
# Reference campaign: 20 trials, 3 nodes, neural-v3, difficulty 2, height 10
python -m verunai.testnet_harness --protocol neural-v3 --difficulty 2 --height 10 --trials 20 --base-seed 1 --output my-run.json

# Quick check (about 5 seconds)
python -m verunai.testnet_harness --trials 1 --difficulty 1 --height 3

# Historical protocols use the same harness
python -m verunai.testnet_harness --protocol bigram-v1 --trials 5 --base-seed 101
python -m verunai.testnet_harness --protocol neural-v2 --trials 5 --base-seed 201

# Fast regression tests (also run in CI)
python -m unittest tests.test_testnet_harness -v
```

| Option | Range | Meaning |
| --- | --- | --- |
| `--protocol` | `bigram-v1`, `neural-v2`, `neural-v3` | Which existing chain every node runs |
| `--nodes` | 3–5 | Number of node processes (full mesh) |
| `--difficulty` | 1–3 | Leading zero hex digits; every node uses the same value |
| `--height` | 2–50 | Nodes stop mining at this height (`--max-blocks`) |
| `--trials` / `--base-seed` | 1–100 / ≥ 0 | Trial *i* uses seed `base-seed + i` |
| `--timeout` | 5–300 s | Launch-to-convergence limit per trial |
| `--sync-interval` | 0.05–5 s | Passed to each node |
| `--no-relays` | flag | Connect nodes directly; disables traffic counting |
| `--output` | new file | Also save the JSON report (refuses to overwrite) |

The command prints the JSON report and exits with status 1 if any trial failed.

## What one trial does

1. Picks free loopback ports. Starts one **counting relay** per node: a byte
   forwarder that never parses or changes data.
2. Starts each node with its own temporary directory, storage file and log,
   peered to every other node *through the relays*. Proxy environment variables
   are removed so traffic stays on loopback.
3. Polls each node's `/status` every 0.1 s. A trial **converges** when all nodes
   report the same head at the target height for 1 s in a row.
4. Reads CPU time, peak memory and relay counters, then stops every node
   (Ctrl+C signal then kill on Linux and macOS; immediate termination on Windows).
   It confirms no process survived.
5. Re-checks every saved chain **twice**, independently: in process with the
   protocol's own `import_and_verify`, and in a fresh `python -m verunai audit`
   process. It then compares each node's ledger fingerprint: height, head,
   balances, v3 sequence numbers, confirmed transfers, model digest and a
   SHA-256 of the canonical export. Any disagreement fails the trial.

### What the seed controls (and what it doesn't)

The seed fixes the miner identities, launch order and launch delays, so a trial's
*configuration* is reproducible. Block contents are **not** reproducible: the
existing node picks random nonce starting points with `os.urandom`, and races
between processes depend on scheduling. The harness therefore records outcomes
rather than claiming bit-for-bit replay. neural-v3 miner addresses come from a
hash and have **no private key**, so their rewards can never be spent.

## Reading the report

`summary`
- `passed` / `failed` / `failures_by_kind`: every failed trial is kept, with its
  kind (`not_converged`, `node_exited`, `startup_timeout`, `ledger_mismatch`,
  `cli_audit_failed`, `orphan_process`, `harness_error`, `port_in_use`) and the
  tail of each node's log.
- `converged_s`, `first_block_s`: seconds from the first launch. These include
  Python start-up of each node.
- `trials_with_reorganization`, `reorganizations_total`: how often a node replaced
  part of its chain with a peer's chain. This counts fork resolution.
- `node_cpu_seconds`, `node_peak_rss_bytes`: per node, read just before shutdown.
- `network_bytes_per_trial`: total node-to-node HTTP bytes through the relays.

`trials[i]` holds the seed, configuration, launch plan, timings, per-node
`/status` counters, resources, relay counts, both audits and the agreed ledger.

### How each value is measured, and its limits

| Value | Source | Limits |
| --- | --- | --- |
| CPU time | Windows `GetProcessTimes`; Linux `/proc/<pid>/stat` | Includes interpreter start-up and import time. Unavailable on other platforms. On Windows inside a virtual environment, the PID is a launcher, so values are marked unavailable rather than reported wrongly. |
| Peak memory | Windows peak working set; Linux `VmHWM` | Whole-process peak, not Python allocations alone |
| Network bytes | Counting relay | Application bytes (HTTP headers + bodies) between nodes only. TCP/IP overhead and harness monitoring are excluded. The relay adds one loopback hop. |
| Timings | Harness `time.monotonic()` | Observation granularity is the 0.1 s poll interval |

## Reference results

**Environment:** Windows 11 build 26300, Python 3.14.5, Intel Family 6 Model 183
with 28 logical CPUs. One machine, uncontrolled background load. Raw data:
[neural-v3](../evidence/v08_p0_neural_v3_three_node.json),
[bigram-v1](../evidence/v08_p0_bigram_v1_three_node.json),
[neural-v2](../evidence/v08_p0_neural_v2_three_node.json).

All runs used 3 nodes, difficulty 2, height 10, relays on.

| Campaign | Trials passed | Converged (median / p95 / max) | CPU per node (median) | Peak memory per node (median) | Node-to-node bytes per trial (median) | Reorganizations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| neural-v3, seeds 1–20 | **20 / 20** | 8.52 / 10.20 / 10.41 s | 6.49 s | 37.2 MB | 290,804 | 98, in all 20 trials |
| bigram-v1, seeds 101–105 | 5 / 5 | 2.08 / 2.12 / 2.12 s | 0.39 s | 37.1 MB | 208,317 | 28, in all 5 trials |
| neural-v2, seeds 201–205 | 5 / 5 | 8.70 / 10.40 / 10.40 s | 7.00 s | 37.0 MB | 258,477 | 28, in all 5 trials |

- No trial failed, no port had to be retried, no block was rejected, and both
  audits agreed on every node in every trial.
- In the neural-v3 campaign the nodes mined 270 blocks locally, but only 200
  entered the final chains, so **70 (26%) were orphaned** by forks. At this very
  low difficulty, simultaneous blocks are common. This is expected and is
  exactly what fork choice has to resolve.
- Thirty passing trials are evidence for these conditions, not a proof that the
  failure probability is zero.

## No blocker found, but four frictions

The existing node supports reliable three-node operation without changes. These
frictions are recorded for later phases. Each has a small, **additive** fix that
is **not** implemented here:

1. **Peers are fixed at start-up**, so ports must be chosen before any node
   binds. Another program could take a port in between. The harness retries the
   trial (none needed). *Fix:* an optional `--ready-file` that records the bound
   port, plus peers that can be added later.
2. **No graceful stop on Windows.** Termination is abrupt. Storage writes use an
   atomic file replacement, so saved chains stayed valid in every trial.
   *Fix:* an HTTP or signal-based shutdown in P2's new node service.
3. **Nonce starting points come from `os.urandom`**, so trials can't be replayed
   exactly. *Fix:* an optional, test-only `--nonce-seed`.
4. **Full-chain sync** (`GET /chain`) means traffic grows with chain length.
   Planned for P3 (incremental sync).

## Design review: fork choice for P3

The v0.8 architecture proposal said "keep the chain first seen" for equal-work
ties. **That recommendation was wrong for this network and is withdrawn.**

### Why first-seen can cause permanent divergence

Under first-seen, a node switches chains only when a competitor has **strictly
more** work. After a network partition heals, each side holds a valid chain of
equal work. Nodes on side A keep A's tip, and nodes on side B keep B's. Neither
chain has more work, so **no node ever switches**. The split ends only if
someone later mines a block that extends one side and that block reaches
everyone.

That escape is unreliable here:
- Nodes stop mining at `--max-blocks`, and operators stop miners. With no further
  block, an equal-height split is **permanent**.
- With few miners split evenly, both sides keep extending their own tips. The
  split can last many rounds.
- A restarted node reloads its own saved tip, which is "first seen" from its
  point of view, so a split can survive restarts.
- The final chain depends on message arrival order, which makes tests
  non-reproducible.

The P0 data shows the risk is not theoretical. Every trial needed
reorganizations, and 26% of mined blocks were orphaned. The nodes stop at the
same height, so ties at the final height are likely. The v0.6 rule resolves them
deterministically; first-seen would leave them unresolved. (The status counters
don't distinguish final-height ties from earlier forks, so this is an inference,
not a direct count.)

### Recommended P3 policy

1. **Primary rule: most cumulative work.** Sum each block's expected attempts
   (16^difficulty) over the chain. While difficulty is fixed, this equals height.
2. **Tie-break: lowest tip hash, compared as a 256-bit integer.** This is the
   rule the v0.6 node already uses. It is deterministic, so once every node has
   seen both tips they all choose the same one, whatever order they saw them in.
   That guarantees convergence after a partition heals, even with mining stopped.
3. **Reorganization depth alert** above K = 6 blocks, recorded in metrics and
   logs. It is not a hard refusal, which would itself cause permanent splits.
4. **Required P3 regression test:** split five nodes 3/2, mine to the same
   height on both sides, stop mining, heal. All nodes must converge. A
   first-seen implementation must fail this test.

**Why this is justified, and its cost.** The private testnet has allowlisted,
cooperating participants, where guaranteed convergence and reproducible tests
matter most. In adversarial settings, how ties are broken affects
"selfish mining" (Eyal and Sirer, *Majority is not Enough*, 2014). A withholding
miner who wins ties gains advantage. Network-position-dependent first-seen can
let a well-connected attacker win most ties. A deterministic hash tie-break gives
any competing block a roughly even chance, similar to the random tie-breaking
those authors proposed. It doesn't eliminate the risk: a miner can still spend
extra work to find a lower-hash competitor. A public network would need its
consensus and incentive design independently reviewed. That review is listed
among the public-deployment blockers.

## Known limitations

- Single machine and loopback only. No real network latency, loss or partitions
  (P6), no authentication (P2), no hostile peers (P4).
- Very low difficulty and fixed full-mesh topology; results don't extrapolate to
  more nodes, higher difficulty or other machines.
- Empty blocks only: no TEST transfers are submitted. Transfer propagation is
  covered by `demo-ledger-process` (two nodes), not by this harness.
- Timing and resource numbers include process start-up and background load.
