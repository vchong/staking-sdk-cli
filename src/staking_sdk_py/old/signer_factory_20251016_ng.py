from abc import ABC, abstractmethod
from typing import Any
from eth_account import Account
from eth_account.datastructures import SignedTransaction
from ledgereth import get_accounts
from web3 import Web3

help(get_accounts)  # Add this line temporarily
print("---")
import inspect

print(inspect.signature(get_accounts))


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
        derivation_path (str): BIP32 derivation path (e.g. default "m/44'/60'/0'/0/0")
    """

    def __init__(self, derivation_path: str = "m/44'/60'/0'/0/0"):
        self.account = get_accounts(path=derivation_path)[0]
        self.address = Web3.to_checksum_address(self.account.address)
        print("LedgerSigner address:", self.address)

    def get_address(self) -> str:
        return self.address

    def sign_transaction(self, tx: dict) -> SignedTransaction:
        # ledgereth account handles the signing
        return self.account.sign_transaction(tx)
