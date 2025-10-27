from abc import ABC, abstractmethod
from typing import Any
from eth_account import Account
from eth_account.datastructures import SignedTransaction

from ledgereth.accounts import get_account_by_path

from ledgereth.transactions import sign_transaction, Type2Transaction
from ledgereth.objects import SignedTransaction as LedgerSignedTransaction

from rlp import encode


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
        self.ledger_account = get_account_by_path(self.derivation_path)
        self.address = self.ledger_account.address
        print("derivation_path:", self.derivation_path)
        print("LedgerSigner address:", self.address)

    def get_address(self) -> str:
        return self.address

    def sign_transaction(self, tx: dict) -> SignedTransaction:
        print("Signing transaction with Ledger")

        # Convert tx dict to ledgereth Type2Transaction
        ledger_tx = Type2Transaction(
            destination=bytes.fromhex(tx["to"][2:]),
            amount=tx["value"],
            gas_limit=tx["gas"],
            data=bytes.fromhex(tx["data"][2:]) if tx.get("data") else b"",
            nonce=tx["nonce"],
            chain_id=tx["chainId"],
            max_priority_fee_per_gas=tx["maxPriorityFeePerGas"],
            max_fee_per_gas=tx["maxFeePerGas"],
            access_list=None,
        )

        signed: LedgerSignedTransaction = sign_transaction(
            ledger_tx, self.derivation_path
        )

        # Convert ledgereth SignedTransaction to raw bytes and parse
        raw_tx = signed.transaction_type.to_byte() + encode(signed, type(signed))

        print("Signing transaction with Ledger - done")

        # Parse raw signed bytes into eth_account SignedTransaction
        # 'Account' has no attribute '_parse_transaction'
        return Account._parse_transaction(raw_tx)
