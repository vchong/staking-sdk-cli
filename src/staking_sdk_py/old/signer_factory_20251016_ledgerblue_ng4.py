from abc import ABC, abstractmethod
from typing import Any
from eth_account import Account
from eth_account.datastructures import SignedTransaction

from ledgerblue.comm import getDongle
from ledgerblue.commException import CommException
from rlp import encode as rlp_encode
from eth_utils import to_bytes, to_int


class Signer(ABC):
    """
    Abstract base class for all signers.
    """

    @abstractmethod
    def get_address(self) -> str:
        pass

    @abstractmethod
    def sign_transaction(self, tx: dict) -> SignedTransaction:
        pass


class LocalSigner(Signer):
    """
    Signer implementation using a local private key.
    """

    def __init__(self, private_key: str):
        print("LocalSigner init")
        self.private_key_hex = (
            private_key[2:] if private_key.startswith("0x") else private_key
        )
        if len(self.private_key_hex) != 64:
            raise ValueError("Private key must be 32 bytes (64 hex characters)")
        print("LocalSigner private_key_hex:", self.private_key_hex)
        self.account = Account.from_key(self.private_key_hex)
        self.address = self.account.address
        print("LocalSigner address:", self.address)

    def get_address(self) -> str:
        return self.address

    def sign_transaction(self, tx: dict) -> SignedTransaction:
        return self.account.sign_transaction(tx)


class LedgerSigner(Signer):
    """
    Signer implementation using a Ledger hardware wallet.

    Args:
        derivation_path (str): BIP32 derivation path (e.g. default "44'/60'/0'/0/0")
    """

    def __init__(self, derivation_path: str = "44'/60'/0'/0/0"):
        if derivation_path.startswith("m/"):
            print("Stripping leading 'm/' from derivation path")
            derivation_path = derivation_path[2:]
        self.derivation_path = derivation_path

        self.dongle = getDongle(True)
        self.address = self._get_address()

        print("derivation_path:", self.derivation_path)
        print("LedgerSigner address:", self.address)

    def _parse_bip32_path(self, path: str) -> bytes:
        import struct

        result = b""
        elements = path.split("/")
        result += struct.pack(">B", len(elements))
        for el in elements:
            if "'" in el:
                val = int(el.replace("'", "")) | 0x80000000
            else:
                val = int(el)
            result += struct.pack(">I", val)
        return result

    def _get_address(self) -> str:
        path_bytes = self._parse_bip32_path(self.derivation_path)
        apdu = bytes.fromhex("e0020000") + bytes([len(path_bytes)]) + path_bytes
        try:
            result = self.dongle.exchange(apdu)
        except CommException as e:
            raise RuntimeError(f"Ledger communication error: {e}")
        addr_len = result[0]
        return result[1 : 1 + addr_len].decode()

    def get_address(self) -> str:
        return self.address

    def sign_transaction(self, tx: dict) -> SignedTransaction:
        """
        Sign a type 2 (EIP-1559) transaction.

        tx dict must include:
        - chainId, nonce, gas, to, value, data (bytes)
        - maxFeePerGas, maxPriorityFeePerGas, type=2
        """

        print("Signing transaction with Ledger")

        if tx.get("type") != 2:
            raise ValueError("Only type 2 transactions are supported")

        # RLP encode type 2 transaction
        tx_payload = [
            to_int(tx["chainId"]),
            to_int(tx["nonce"]),
            to_int(tx["maxPriorityFeePerGas"]),
            to_int(tx["maxFeePerGas"]),
            to_int(tx["gas"]),
            bytes.fromhex(tx["to"][2:]) if tx["to"] else b"",
            to_int(tx["value"]),
            tx.get("data", b""),
            tx.get("accessList", []),
        ]
        rlp_bytes = b"\x02" + rlp_encode(tx_payload)

        # APDU command (works for small transactions <255 bytes)
        apdu = bytes([0xE0, 0x04, 0x00, 0x00, len(rlp_bytes)]) + rlp_bytes
        try:
            signed_bytes = self.dongle.exchange(apdu)
        except CommException as e:
            raise RuntimeError(f"Ledger signing error: {e}")

        print("Signing transaction with Ledger - done")

        # Parse raw signed bytes into eth_account SignedTransaction
        return Account._parse_transaction(signed_bytes)
