"""
Tests RPC storage
"""

import pytest
from starkware.starknet.public.abi import get_storage_var_address

from .rpc_utils import rpc_call, get_block_with_transaction


def test_get_storage_at(deploy_info):
    """
    Get storage at address
    """
    contract_address: str = deploy_info["address"]
    key: str = hex(get_storage_var_address("balance"))
    block_hash: str = "latest"

    resp = rpc_call(
        "starknet_getStorageAt", params={
            "contract_address": contract_address,
            "key": key,
            "block_hash": block_hash,
        }
    )
    storage = resp["result"]

    assert storage == "0x0"


# pylint: disable=unused-argument
def test_get_storage_at_raises_on_incorrect_contract(deploy_info):
    """
    Get storage at incorrect contract
    """
    key: str = hex(get_storage_var_address("balance"))
    block_hash: str = "latest"

    ex = rpc_call(
        "starknet_getStorageAt", params={
            "contract_address": "0x0",
            "key": key,
            "block_hash": block_hash,
        }
    )

    assert ex["error"] == {
        "code": 20,
        "message": "Contract not found"
    }


# internal workings of get_storage_at would have to be changed for this to work
# since currently it will (correctly) return 0x0 for any incorrect key
@pytest.mark.xfail
def test_get_storage_at_raises_on_incorrect_key(deploy_info):
    """
    Get storage at incorrect key
    """
    block = get_block_with_transaction(deploy_info["transaction_hash"])

    contract_address: str = deploy_info["address"]
    block_hash: str = block["block_hash"]

    ex = rpc_call(
        "starknet_getStorageAt", params={
            "contract_address": contract_address,
            "key": "0x0",
            "block_hash": block_hash,
        }
    )

    assert ex["error"] == {
        "code": 23,
        "message": "Invalid storage key"
    }


# This will fail as get_storage_at only supports "latest" as block_hash
# and will fail with custom exception if other is provided
@pytest.mark.xfail
def test_get_storage_at_raises_on_incorrect_block_hash(deploy_info):
    """
    Get storage at incorrect block hash
    """

    contract_address: str = deploy_info["address"]
    key: str = hex(get_storage_var_address("balance"))

    ex = rpc_call(
        "starknet_getStorageAt", params={
            "contract_address": contract_address,
            "key": key,
            "block_hash": "0x0",
        }
    )

    assert ex["error"] == {
        "code": 24,
        "message": "Invalid block hash"
    }
