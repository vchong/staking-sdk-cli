from abc import ABC, abstractmethod
from typing import Any
from eth_account import Account
from eth_account.datastructures import SignedTransaction


from eth_account._utils.typed_transactions import Type2Transaction
from ledgereth.accounts import get_account_by_path
from ledgereth.transactions import sign_transaction


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

        # convert tx to format accepted by ledgereth
        tx_obj = Type2Transaction(
            chainId=tx["chainId"],
            nonce=tx["nonce"],
            maxPriorityFeePerGas=tx["maxPriorityFeePerGas"],
            maxFeePerGas=tx["maxFeePerGas"],
            gas=tx["gas"],
            to=tx["to"],
            value=tx["value"],
            data=tx.get("data", b""),
            accessList=tx.get("accessList", []),
        )
        signed_bytes = sign_transaction(tx_obj, self.derivation_path)

        print("Signing transaction with Ledger - done")

        # Parse raw signed bytes into eth_account SignedTransaction
        return Account._parse_transaction(signed_bytes)
