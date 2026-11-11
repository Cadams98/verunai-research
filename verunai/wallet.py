"""Research-only signing identities for the neural-v3 TEST ledger.

Ed25519 is a well-established signature scheme, but this wallet format is an
unaudited prototype. No real funds and no real mainnet private keys.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from .core import canonical_bytes, sha256

ADDRESS_RE = re.compile(r"vr[0-9a-f]{38}\Z")
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
HEX128_RE = re.compile(r"[0-9a-f]{128}\Z")
TX_DOMAIN = "verunai-neural-v3-transfer-research-2026"
MAX_AMOUNT = 10**12


def address_from_public_hex(public_hex: str) -> str:
    if not isinstance(public_hex, str) or not HEX64_RE.fullmatch(public_hex):
        raise ValueError("Public key must be 32 lowercase hex bytes")
    return "vr" + hashlib.blake2s(bytes.fromhex(public_hex), digest_size=32).hexdigest()[:38]


def public_from_private_hex(private_hex: str) -> str:
    if not isinstance(private_hex, str) or not HEX64_RE.fullmatch(private_hex):
        raise ValueError("Private key must be 32 lowercase hex bytes")
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex))
    raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()


@dataclass(frozen=True)
class Wallet:
    private_hex: str

    @classmethod
    def generate(cls) -> "Wallet":
        private = Ed25519PrivateKey.generate()
        return cls(private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        ).hex())

    @property
    def public_hex(self) -> str:
        return public_from_private_hex(self.private_hex)

    @property
    def address(self) -> str:
        return address_from_public_hex(self.public_hex)

    def sign(self, data: bytes) -> str:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(self.private_hex)).sign(data).hex()

    def save(self, filepath: str | Path) -> None:
        """Create a new file, refusing overwrite. Keep private wallets off public GitHub."""
        path = Path(filepath)
        content = json.dumps({"research_only": True, "format": "verunai-v3-ed25519-raw", "private_key": self.private_hex}, indent=2) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)

    @classmethod
    def load(cls, filepath: str | Path) -> "Wallet":
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        if data.get("format") != "verunai-v3-ed25519-raw":
            raise ValueError("Not a Verunai research wallet")
        wallet = cls(data["private_key"])
        _ = wallet.public_hex
        return wallet


@dataclass(frozen=True)
class Transfer:
    """Account transfer, with monotonically increasing sender sequence."""
    sender_pubkey: str
    recipient: str
    amount: int
    fee: int
    sequence: int
    signature: str

    @property
    def sender(self) -> str:
        return address_from_public_hex(self.sender_pubkey)

    def unsigned(self) -> dict:
        return {"domain": TX_DOMAIN, "pubkey": self.sender_pubkey, "to": self.recipient,
                "amount": self.amount, "fee": self.fee, "sequence": self.sequence}

    def to_dict(self) -> dict:
        return {**self.unsigned(), "signature": self.signature}

    @property
    def txid(self) -> str:
        return sha256(canonical_bytes(self.to_dict()))

    @classmethod
    def from_dict(cls, data: dict) -> "Transfer":
        if not isinstance(data, dict) or set(data) != {"domain", "pubkey", "to", "amount", "fee", "sequence", "signature"}:
            raise ValueError("Malformed transfer")
        if data["domain"] != TX_DOMAIN:
            raise ValueError("Invalid transfer domain")
        tx = cls(data["pubkey"], data["to"], data["amount"], data["fee"], data["sequence"], data["signature"])
        tx.verify()
        return tx

    def verify(self) -> None:
        if not isinstance(self.sender_pubkey, str) or not HEX64_RE.fullmatch(self.sender_pubkey):
            raise ValueError("Invalid sender public key")
        if not isinstance(self.recipient, str) or not ADDRESS_RE.fullmatch(self.recipient):
            raise ValueError("Invalid recipient address")
        if type(self.amount) is not int or not 1 <= self.amount <= MAX_AMOUNT:
            raise ValueError("Invalid amount")
        if type(self.fee) is not int or not 0 <= self.fee <= MAX_AMOUNT:
            raise ValueError("Invalid fee")
        if self.amount + self.fee > MAX_AMOUNT:
            raise ValueError("Transfer total exceeds limit")
        if type(self.sequence) is not int or not 0 <= self.sequence < 2**53:
            raise ValueError("Invalid sequence")
        if not isinstance(self.signature, str) or not HEX128_RE.fullmatch(self.signature):
            raise ValueError("Invalid signature format")
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.sender_pubkey)).verify(
                bytes.fromhex(self.signature), canonical_bytes(self.unsigned()))
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("Invalid transfer signature") from exc


def sign_transfer(wallet: Wallet, recipient: str, amount: int, fee: int, sequence: int) -> Transfer:
    unsigned = Transfer(wallet.public_hex, recipient, amount, fee, sequence, "")
    # Verify field shape without requiring a signature first.
    if not ADDRESS_RE.fullmatch(recipient) or type(amount) is not int or not 1 <= amount <= MAX_AMOUNT:
        raise ValueError("Invalid recipient or amount")
    if type(fee) is not int or not 0 <= fee <= MAX_AMOUNT or amount + fee > MAX_AMOUNT:
        raise ValueError("Invalid fee or total")
    if type(sequence) is not int or not 0 <= sequence < 2**53:
        raise ValueError("Invalid sequence")
    signed = Transfer(wallet.public_hex, recipient, amount, fee, sequence,
                      wallet.sign(canonical_bytes(unsigned.unsigned())))
    signed.verify()
    return signed
