import os

from staking_sdk_py.signer_factory import Signer, LocalSigner, LedgerSigner
from src.logger import init_logging


def create_signer(config: dict) -> Signer:
    log = init_logging(config["log_level"].upper())
    signer_type = os.environ.get("SIGNER_TYPE")
    if not signer_type:
        if config.get("staking", {}).get("funded_address_private_key"):
            signer_type = "legacy"
        else:
            signer_type = config["signer"].get("type", "local").lower()
    if not signer_type:
        raise ValueError(
            "signer_type is required as SIGNER_TYPE env var or in config file"
        )

    # For backwards compatibility
    if signer_type == "legacy":
        log.debug(f"Initializing legacy signer")
        private_key = os.environ.get("FUNDED_ACCOUNT_PRIVATE_KEY")
        if not private_key:
            private_key = config["staking"]["funded_address_private_key"]
        if not private_key:
            raise ValueError(
                "private_key is required as FUNDED_ACCOUNT_PRIVATE_KEY env var or in config file"
            )
        log.debug(f"Legacy signer initialized")
        return LocalSigner(private_key)

    elif signer_type == "local":
        log.debug(f"Initializing local signer")
        private_key = os.environ.get("PRIVATE_KEY")
        if not private_key:
            private_key = config["signer"]["private_key"]
        if not private_key:
            raise ValueError(
                "private_key is required as PRIVATE_KEY env var or in config file"
            )
        log.debug(f"Local signer initialized")
        return LocalSigner(private_key)

    elif signer_type == "ledger":
        log.debug(f"Initializing ledger signer")
        derivation_path = os.environ.get("DERIVATION_PATH")
        if not derivation_path:
            derivation_path = config["signer"].get("derivation_path", "44'/60'/0'/0/0")
        if not derivation_path:
            raise ValueError(
                "derivation_path is required as DERIVATION_PATH env var or in config file"
            )
        log.debug(f"Ledger signer initialized")
        return LedgerSigner(derivation_path)

    else:
        raise ValueError(
            f"Invalid signer.type: {signer_type}. Must be 'local' or 'ledger'"
        )
