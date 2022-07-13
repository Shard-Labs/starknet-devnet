"""
Tests RPC contract class
"""

from .rpc_utils import rpc_call


def test_get_class(class_hash):
    """
    Test get contract class
    """
    resp = rpc_call(
        "starknet_getClass",
        params={"class_hash": class_hash}
    )
    contract_class = resp["result"]

    assert contract_class["entry_points_by_type"] == {
        "CONSTRUCTOR": [],
        "EXTERNAL": [
            {"offset": "0x03a", "selector": "0x0362398bec32bc0ebb411203221a35a0301193a96f317ebe5e40be9f60d15320"},
            {"offset": "0x05b", "selector": "0x039e11d48192e4333233c7eb19d10ad67c362bb28580c604d67884c85da39695"}
        ],
        "L1_HANDLER": []
    }
    assert isinstance(contract_class["program"], str)


def test_get_class_hash_at(deploy_info, class_hash):
    """
    Test get contract class at given hash
    """
    contract_address: str = deploy_info["address"]

    resp = rpc_call(
        "starknet_getClassHashAt",
        params={"contract_address": contract_address}
    )
    rpc_class_hash = resp["result"]

    assert rpc_class_hash == class_hash


def test_get_class_at(deploy_info):
    """
    Test get contract class at given contract address
    """
    contract_address: str = deploy_info["address"]

    resp = rpc_call(
        "starknet_getClassAt",
        params={"contract_address": contract_address}
    )
    contract_class = resp["result"]

    assert contract_class["entry_points_by_type"] == {
        "CONSTRUCTOR": [],
        "EXTERNAL": [
            {"offset": "0x03a", "selector": "0x0362398bec32bc0ebb411203221a35a0301193a96f317ebe5e40be9f60d15320"},
            {"offset": "0x05b", "selector": "0x039e11d48192e4333233c7eb19d10ad67c362bb28580c604d67884c85da39695"}
        ],
        "L1_HANDLER": []
    }
    assert isinstance(contract_class["program"], str)
