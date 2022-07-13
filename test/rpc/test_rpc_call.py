"""
Tests RPC rpc_call
"""

import pytest
from starkware.starknet.public.abi import get_selector_from_name

from .rpc_utils import rpc_call


def test_call(deploy_info):
    """
    Call contract
    """
    contract_address: str = deploy_info["address"]

    resp = rpc_call(
        "starknet_call", params={
            "contract_address": contract_address,
            "entry_point_selector": hex(get_selector_from_name("get_balance")),
            "calldata": [],
            "block_hash": "latest"
        }
    )
    result = resp["result"]

    assert isinstance(result["result"], list)
    assert len(result["result"]) == 1
    assert result["result"][0] == "0x0"


# pylint: disable=unused-argument
def test_call_raises_on_incorrect_contract_address(deploy_info):
    """
    Call contract with incorrect address
    """
    ex = rpc_call(
        "starknet_call", params={
            "contract_address": "0x07b529269b82f3f3ebbb2c463a9e1edaa2c6eea8fa308ff70b30398766a2e20c",
            "entry_point_selector": hex(get_selector_from_name("get_balance")),
            "calldata": [],
            "block_hash": "latest"
        }
    )

    assert ex["error"] == {
        "code": 20,
        "message": "Contract not found"
    }


def test_call_raises_on_incorrect_selector(deploy_info):
    """
    Call contract with incorrect entry point selector
    """
    contract_address: str = deploy_info["address"]

    ex = rpc_call(
        "starknet_call", params={
            "contract_address": contract_address,
            "entry_point_selector": hex(get_selector_from_name("xxxxxxx")),
            "calldata": [],
            "block_hash": "latest"
        }
    )

    assert ex["error"] == {
        "code": 21,
        "message": "Invalid message selector"
    }


def test_call_raises_on_invalid_calldata(deploy_info):
    """
    Call contract with incorrect calldata
    """
    contract_address: str = deploy_info["address"]

    ex = rpc_call(
        "starknet_call", params={
            "contract_address": contract_address,
            "entry_point_selector": hex(get_selector_from_name("get_balance")),
            "calldata": ["a", "b", "123"],
            "block_hash": "latest"
        }
    )

    assert ex["error"] == {
        "code": 22,
        "message": "Invalid call data"
    }


# This test will fail since we are throwing a custom error block_hash different from `latest`
@pytest.mark.xfail
def test_call_raises_on_incorrect_block_hash(deploy_info):
    """
    Call contract with incorrect block hash
    """
    contract_address: str = deploy_info["address"]

    ex = rpc_call(
        "starknet_call", params={
            "contract_address": contract_address,
            "entry_point_selector": hex(get_selector_from_name("get_balance")),
            "calldata": [],
            "block_hash": "0x0"
        }
    )

    assert ex["error"] == {
        "code": 24,
        "message": "Invalid block hash"
    }
