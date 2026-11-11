"""Command line interface for the single-process prototype."""
import argparse
import json
from pathlib import Path
from .core import Chain, mine_round_robin
from .neural_consensus import NeuralChain, mine_neural
from .neural_v3 import LedgerChain
from .wallet import Wallet, sign_transfer
from .ledger_demo import demo_ledger
from .ledger_process_demo import demo_ledger_process
from .adversarial_audit import audit_work_asymmetry
from .benchmark import benchmark
from .network import TestnetNode, request_json
from .demo import demo_testnet
from .gpu_research import neural_benchmark
from .neural_benchmark import benchmark_neural
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="Verunai educational AI-bound mining prototype")
    sub = parser.add_subparsers(dest="command", required=True)
    mine = sub.add_parser("mine", help="Mine blocks with simulated miners")
    mine.add_argument("--blocks", type=int, default=5)
    mine.add_argument("--protocol", choices=("bigram-v1", "neural-v2"), default="bigram-v1")
    mine.add_argument("--backend", choices=("python", "torch-cpu", "torch-cuda"), default="python")
    mine.add_argument("--difficulty", type=int, default=2)
    mine.add_argument("--powers", default="1,2,5", help="Comma-separated relative attempts/round per miner")
    mine.add_argument("--output", default="", help="Optional path for verifiable chain JSON")
    audit = sub.add_parser("audit", help="Replay and verify a saved blockchain")
    audit.add_argument("chain_file", help="JSON written by 'mine --output'")
    bench = sub.add_parser("benchmark", help="Measure toy CPU mining vs block replay")
    bench.add_argument("--attempts", type=int, default=2000)
    nbench = sub.add_parser("neural-mining-benchmark", help="Compare v2 neural candidates and full validation")
    nbench.add_argument("--attempts", type=int, default=150)
    nbench.add_argument("--backend", choices=("python", "torch-cpu", "torch-cuda"), default="python")
    node = sub.add_parser("node", help="Start an independent PRIVATE testnet node (not public Internet safe)")
    node.add_argument("--miner", required=True, help="Miner label (v1/v2) or wallet address (neural-v3)")
    node.add_argument("--protocol", choices=("bigram-v1", "neural-v2", "neural-v3"), default="bigram-v1")
    node.add_argument("--backend", choices=("python", "torch-cpu", "torch-cuda"), default="python")
    node.add_argument("--host", default="127.0.0.1", help="Bind address; default is localhost only")
    node.add_argument("--allow-lan", action="store_true", help="Acknowledge unauthenticated LAN risk")
    node.add_argument("--port", type=int, default=8080)
    node.add_argument("--peer", action="append", default=[], help="Peer URL; repeat for multiple peers")
    node.add_argument("--difficulty", type=int, default=2)
    node.add_argument("--mine", action="store_true", help="Mine fictional nontransferable TEST rewards")
    node.add_argument("--mine-after-tx", action="store_true", help="Research demo: wait for pending v3 transfer before mining")
    node.add_argument("--max-blocks", type=int, default=0, help="Stop mining at height; 0 = no limit")
    node.add_argument("--storage", default="", help="Path for verified chain persistence")
    node.add_argument("--sync-interval", type=float, default=0.5)
    demo = sub.add_parser("demo-testnet", help="Launch two OS-process miners and prove convergence")
    demo.add_argument("--blocks", type=int, default=8)
    demo.add_argument("--protocol", choices=("bigram-v1", "neural-v2"), default="bigram-v1")
    demo.add_argument("--backend", choices=("python", "torch-cpu", "torch-cuda"), default="python")
    demo.add_argument("--difficulty", type=int, default=2)
    demo.add_argument("--timeout", type=float, default=30)
    status = sub.add_parser("status", help="Query a local testnet node")
    status.add_argument("--url", default="http://127.0.0.1:8080")
    gpu = sub.add_parser("gpu-benchmark", help="Opt-in real neural training benchmark (requires PyTorch)")
    gpu.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    gpu.add_argument("--steps", type=int, default=30)
    gpu.add_argument("--width", type=int, default=128)
    gpu.add_argument("--batch", type=int, default=64)
    wallet = sub.add_parser("wallet-new", help="Create neural-v3 disposable test wallet (do NOT use for real assets)")
    wallet.add_argument("--output", required=True, help="New file; refuses overwrites")
    send = sub.add_parser("send-test", help="Send a signed fictional TEST transfer to a local neural-v3 node")
    send.add_argument("--wallet", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--amount", type=int, required=True)
    send.add_argument("--fee", type=int, default=0)
    send.add_argument("--node", default="http://127.0.0.1:8080")
    sub.add_parser("demo-ledger", help="Mine, sign, transfer, confirm, and replay on two local HTTP nodes")
    proc = sub.add_parser("demo-ledger-process", help="Reproduce payment mining with two independent OS processes")
    proc.add_argument("--timeout", type=float, default=35)
    sec = sub.add_parser("security-audit", help="Measure fake-header cost asymmetry in research protocol")
    sec.add_argument("--samples", type=int, default=50)
    args = parser.parse_args()
    if args.command == "wallet-new":
        try:
            wallet_obj = Wallet.generate()
            wallet_obj.save(args.output)
            print(json.dumps({"result": "TEST_WALLET_CREATED", "path": args.output,
                              "address": wallet_obj.address,
                              "warning": "Disposable research identity. DO NOT use for real assets or commit private keys."}, indent=2))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
    elif args.command == "send-test":
        try:
            wallet_obj = Wallet.load(args.wallet)
            status_data = request_json(args.node.rstrip("/") + "/status", limit=16_000)
            if status_data.get("protocol_mode") != "neural-v3":
                raise ValueError("Target node must use neural-v3")
            sequence = int(status_data.get("sequences", {}).get(wallet_obj.address, 0))
            tx = sign_transfer(wallet_obj, args.to, args.amount, args.fee, sequence)
            result = request_json(args.node.rstrip("/") + "/tx", {"transfer": tx.to_dict()}, limit=4096)
            print(json.dumps({"transaction_id": tx.txid, "sender": tx.sender,
                              "recipient": tx.recipient, "amount_TEST": tx.amount,
                              "fee_TEST": tx.fee, "node_response": result,
                              "warning": "Test transfer only; no market value"}, indent=2))
        except (ValueError, OSError, KeyError) as exc:
            parser.error(str(exc))
    elif args.command == "demo-ledger":
        try:
            print(json.dumps(demo_ledger(), indent=2))
        except (ValueError, OSError, RuntimeError) as exc:
            parser.error(str(exc))
    elif args.command == "demo-ledger-process":
        try:
            print(json.dumps(demo_ledger_process(timeout=args.timeout), indent=2))
        except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
            parser.error(str(exc))
    elif args.command == "security-audit":
        try:
            print(json.dumps(audit_work_asymmetry(args.samples), indent=2))
        except (ValueError, RuntimeError) as exc:
            parser.error(str(exc))
    elif args.command == "mine":
        if not 1 <= args.blocks <= 1000:
            parser.error("--blocks must be 1-1000")
        try:
            values = [int(s) for s in args.powers.split(",")]
            powers = {f"miner{i+1}": v for i, v in enumerate(values)}
            if args.protocol == "neural-v2":
                chain = NeuralChain(args.difficulty)
                loss = lambda: chain.training_loss()
                unit = "MSE"
                winner = lambda: mine_neural(chain, powers, backend=args.backend)
            else:
                if args.backend != "python":
                    parser.error("Torch backend requires --protocol neural-v2")
                chain = Chain(args.difficulty)
                loss = lambda: chain.cross_entropy()
                unit = "cross-entropy"
                winner = lambda: mine_round_robin(chain, powers)
            print(f"Starting {args.protocol} training {unit}: {loss():.4f} (lower is better)")
            for _ in range(args.blocks):
                block, attempts = winner()
                print(f"Block {block.height:>3} | winner={block.miner:<9} "
                      f"reward={block.reward:>3} TEST | attempts={attempts:>5} | "
                      f"AI {unit}={loss():.4f} | hash={block.hash[:16]}...")
            print(f"Final balances: {chain.balances} (fictional, nontransferable TEST units)")
            if args.output:
                Path(args.output).write_text(json.dumps(chain.export(), indent=2), encoding="utf-8")
                print(f"Wrote {args.output}")
        except (ValueError, RuntimeError) as e:
            parser.error(str(e))
    elif args.command == "benchmark":
        try:
            print(json.dumps(benchmark(args.attempts), indent=2))
        except ValueError as e:
            parser.error(str(e))
    elif args.command == "neural-mining-benchmark":
        try:
            print(json.dumps(benchmark_neural(args.attempts, backend=args.backend), indent=2))
        except (ValueError, RuntimeError, AssertionError) as exc:
            parser.error(str(exc))
    elif args.command == "gpu-benchmark":
        try:
            print(json.dumps(neural_benchmark(args.steps, args.width, args.batch, args.device), indent=2))
        except (ValueError, RuntimeError) as exc:
            parser.error(str(exc))
    elif args.command == "demo-testnet":
        try:
            result = demo_testnet(args.blocks, args.difficulty, args.timeout,
                                  mode=args.protocol, backend=args.backend)
            print(json.dumps(result, indent=2))
        except (ValueError, TimeoutError, RuntimeError, OSError) as exc:
            parser.error(f"Two-process demo failed: {exc}")
    elif args.command == "status":
        try:
            print(json.dumps(request_json(args.url.rstrip("/") + "/status", limit=16_000), indent=2))
        except (OSError, ValueError) as exc:
            parser.error(f"Node query failed: {exc}")
    elif args.command == "node":
        if args.host not in ("localhost", "127.0.0.1", "::1") and not args.allow_lan:
            parser.error("Non-loopback bind requires --allow-lan; NEVER expose to public Internet")
        if not 0 <= args.port <= 65535:
            parser.error("port must be 0..65535")
        try:
            server = TestnetNode(miner=args.miner, difficulty=args.difficulty,
                                 peers=args.peer, storage=args.storage or None,
                                 mine=args.mine, max_blocks=args.max_blocks,
                                 sync_interval=args.sync_interval, mode=args.protocol,
                                 backend=args.backend, mine_after_tx=args.mine_after_tx)
            port = server.start(host=args.host, port=args.port)
            print(f"VERUNAI PRIVATE research node {args.miner} listening on {args.host}:{port}", flush=True)
            print("WARNING: unauthenticated toy protocol; fake TEST rewards only. Ctrl+C to stop.", flush=True)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Shutting down node...", flush=True)
            finally:
                server.stop()
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    elif args.command == "audit":
        try:
            data = json.loads(Path(args.chain_file).read_text(encoding="utf-8"))
            mode = data.get("protocol_version")
            if mode == 1:
                chain = Chain.import_and_verify(data)
                print(f"VALID v1: {len(chain.blocks)} blocks, head={chain.head}")
                print(f"Verified balances: {chain.balances}; cross-entropy={chain.cross_entropy():.4f}")
            elif mode == 2:
                chain = NeuralChain.import_and_verify(data)
                print(f"VALID neural-v2: {len(chain.blocks)} blocks, head={chain.head}")
                print(f"Verified balances: {chain.balances}; in-sample MSE={chain.training_loss():.4f}")
            elif mode == 3:
                chain = LedgerChain.import_and_verify(data)
                print(f"VALID neural-v3: {len(chain.blocks)} blocks, head={chain.head}")
                print(f"Verified balances: {chain.balances}; confirmed transfers={len(chain.included_txids)}")
            else:
                raise ValueError("Unknown protocol version")
        except (ValueError, KeyError, TypeError, OSError) as e:
            parser.error(f"Chain rejected: {e}")


if __name__ == "__main__":
    main()
