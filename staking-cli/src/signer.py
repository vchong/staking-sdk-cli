import os
import sys

from staking_sdk_py.signer_factory import Signer, LocalSigner, LedgerSigner


def create_signer(config: dict) -> Signer:
    # print("create_signer")

    signer_type = os.environ.get("SIGNER_TYPE")
    if not signer_type:
        signer_type = config["signer"].get("type", "local").lower()
    if not signer_type:
        raise ValueError(
            "signer_type is required as SIGNER_TYPE env var or in config file"
        )

    if signer_type == "local":
        print("local signer")

        private_key = os.environ.get("PRIVATE_KEY")
        if not private_key:
            private_key = config["signer"].get("private_key")
        if not private_key:
            raise ValueError(
                "private_key is required as PRIVATE_KEY env var or in config file"
            )
        return LocalSigner(private_key)

    elif signer_type == "ledger":
        print("ledger signer")

        derivation_path = os.environ.get("DERIVATION_PATH")
        if not derivation_path:
            derivation_path = config["signer"].get("derivation_path", "44'/60'/0'/0/0")
        if not derivation_path:
            raise ValueError(
                "derivation_path is required as DERIVATION_PATH env var or in config file"
            )
        return LedgerSigner(derivation_path)

    else:
        raise ValueError(
            f"Invalid signer.type: {signer_type}. Must be 'local' or 'ledger'"
        )
