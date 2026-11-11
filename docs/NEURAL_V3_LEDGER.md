# Neural-v3 signed TEST ledger — experimental protocol

**Status: LOCAL RESEARCH ONLY. Not a coin, mainnet, investment, or secure permissionless blockchain.**

Version `3` is separate from v1 and v2. Existing v2 chains do not replay as v3. It combines the v2 nonce-selected, small, integer-exact neural gradient step with a **signed account-transfer ledger** for fictional TEST units.

## Architecture

- **Identity:** `cryptography` Ed25519 raw 32-byte public/private keys. Addresses are `vr` plus the first 38 lowercase hexadecimal digits of a BLAKE2s digest of the public key. Address truncation and all wallet serialization are research conventions, NOT independently reviewed wallet standards.
- **Miner reward:** The block header's 40-character `miner` field is a recipient address. As in other blockchains, a miner may designate someone else's recipient address; **creating a block doesn't authorize spending the recipient's balance**.
- **Transfer fields:** Domain-separated signing bytes include the sender public key, destination address, positive integer amount, integer nonnegative fee, and sender account sequence.
- **State:** Balance and next sequence per address. Signatures bind spending authority; sequences prevent simple replay. A transaction spends `amount + fee`, credits `amount` to the receiver, and routes the fee to the winning block miner. The existing block subsidy is 50 TEST.
- **Atomicity:** All transactions must validate before balances or model state are updated. Bad blocks are rejected without changing the chain.
- **Consensus:** Every node independently recomputes gradient and model digest for each accepted block. Each block hash must meet a small experimental SHA-256 difficulty target. There is **no proof that candidate AI work cannot be bypassed or drastically optimized**.
- **No real economic network:** No stable mainnet, transactions on a public network, real coin, supply schedule, finality guarantee, transaction marketplace, consensus difficulty retargeting, independent validator incentives, secure peer discovery or wallet recovery protocol.

## Install

Python 3.10+ is required, plus the maintained `cryptography` package. From this project's root directory:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

On Windows, `py -3` can replace `python`. A convenience launcher `RUN_V3_LEDGER_DEMO_WINDOWS.bat` is included.

## Fast demonstration: two independent Python processes

```bash
python -m verunai demo-ledger-process
```

The script boots two separate OS processes bound to 127.0.0.1. Alice mines a block rewarding a disposable address with 50 TEST. Bob connects, synchronizes, then receives a signed 12 TEST transfer from Alice with a 1 TEST fee. Bob mines the confirmation block and earns 50 TEST + 1 TEST fee. Expected balances:

- Alice: `50 - 12 - 1 = 37 TEST`
- Bob: `12 + 50 + 1 = 63 TEST`
- Total supply: `100 TEST` (exactly two mining subsidies; fees only transfer existing TEST)

Both nodes agree on block height and hash, and their model digests are compared. A separate replay revalidates signatures, transfers, rewards, neural gradients and model state.

## Interactive test wallets

Create two disposable wallets (NEVER commit wallet files to public GitHub):

```bash
python -m verunai wallet-new --output alice.wallet.json
python -m verunai wallet-new --output bob.wallet.json
```

Run an isolated node, specifying its own **wallet address** as `--miner` and `--protocol neural-v3`:

```bash
python -m verunai node --protocol neural-v3 --miner vrYOUR40CHARADDRESS --port 8101 --mine --difficulty 1 --storage alice-chain.json
```

In a second terminal, check status (find the balance and sequence):

```bash
python -m verunai status --url http://127.0.0.1:8101
```

Once Alice has mined test funds, send a signed payment to Bob's address:

```bash
python -m verunai send-test --wallet alice.wallet.json --to vrBOBS40CHARADDRESS --amount 12 --fee 1 --node http://127.0.0.1:8101
```

Transfers remain pending until a miner includes them in a block. You can inspect pending transfers with `GET /mempool`, chain data with `GET /chain`, node statistics with `GET /status`, and model metadata with `GET /model`. The node HTTP service is **unauthenticated and for local/isolated research only**.

### Important wallet warnings

The experimental wallet file contains a plain-text private key. On POSIX, the program requests `0600` file permissions; on Windows, file security depends on the account and directory ACLs. Do not put real funds into these addresses, reuse these keys on other chains, or upload them to GitHub or AI chat tools.

## Known design limitations

1. **Useful-work consensus is unsolved.** The model is small and static, the data is an embedded repetitive text corpus, nonce-derived batches can be optimized, and SHA-256 chooses winners. Verifiers recompute the entire gradient. Block mining cannot honestly be described as an established new secure proof of useful work.
2. **PoW security is not achieved.** The demo uses easy fixed difficulty, simplistic highest-height fork choice and unauthenticated HTTP peers. An adversary could cheaply create competing histories or disrupt nodes.
3. **Signature security ≠ network security.** Ed25519 protects transaction authorization, not network availability, peer identity, confirmation finality, or key storage.
4. **No persistent mempool.** Pending transfers are in-memory; losing branches can orphan transactions and do not automatically restore all unconfirmed payments.
5. **Denial-of-service risks.** Validators repeat relatively expensive training computations. A malicious peer can grind cheap but false headers to force verification work.
6. **No real economics.** TEST units cannot be sold, spent outside the simulation, or converted into any cryptocurrency. Any future publicly transferable token launch would require extensive external security and legal review.

Read `docs/SECURITY_FINDINGS_V06.md` and `docs/NEURAL_V2_PROTOCOL.md` before modifying consensus.
