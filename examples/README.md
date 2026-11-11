# Working examples (safe test units only)

Run examples from the **repository root** after `python -m pip install -e .`.

```bash
# Local neural-v3 signed payment between separate processes
python -m verunai demo-ledger-process

# Local two-process neural-v2 testnet
python -m verunai demo-testnet --protocol neural-v2 --blocks 5 --difficulty 1

# Validate a saved, historical research chain
python -m verunai audit evidence/demo_chain.json
```

Do not run node networking on public interfaces or use real funds. These are research demonstrations. New examples belong here **only when they are small standalone examples**; reusable production code belongs inside `verunai/`, tests inside `tests/`, and generated data in ignored output paths.
