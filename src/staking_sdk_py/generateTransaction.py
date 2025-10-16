import binascii
import web3
from web3 import Web3

from staking_sdk_py.signer_factory import Signer

def send_transaction(
    w3: Web3,
    signer:Signer,
    to: str,
    data: str,
    chain_id: int,
    value: int = 0,
    gas_limit: int = 1_000_000,
    max_fee_per_gas: int = 500_000_000_000,
    max_priority_fee_per_gas: int = 1_000_000_000,
) -> str:
    nonce = w3.eth.get_transaction_count(signer.get_address())

    tx = {
        "to": Web3.to_checksum_address(to),
        "value": value,
        "data": data,
        "nonce": nonce,
        "gas": gas_limit,
        "maxFeePerGas": max_fee_per_gas,
        "maxPriorityFeePerGas": max_priority_fee_per_gas,
        "chainId": chain_id,
        "type": 2  # EIP-1559 transaction
    }

    # print("tx:", tx)
    signed_tx = signer.sign_transaction(tx)
    print("signed_tx (hex):", binascii.hexlify(signed_tx.raw_transaction).decode())
    # tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash = bytes.fromhex(
                "e71a993723643a51d9a978d969af88cdb3e4c0f811ecb37dce451427cda47d04"
            )
    return tx_hash.hex()
