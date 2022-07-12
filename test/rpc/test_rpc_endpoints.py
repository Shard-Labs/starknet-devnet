"""
Tests RPC endpoints.
"""
# pylint: disable=too-many-lines
from __future__ import annotations

import json
from typing import Union

from starkware.starknet.public.abi import get_storage_var_address
from starkware.starknet.core.os.class_hash import compute_class_hash

from starknet_devnet.server import app
from starknet_devnet.general_config import DEFAULT_GENERAL_CONFIG


def rpc_call(method: str, params: Union[dict, list]) -> dict:
    """
    Make a call to the RPC endpoint
    """
    req = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 0
    }

    resp = app.test_client().post(
        "/rpc",
        content_type="application/json",
        data=json.dumps(req)
    )
    result = json.loads(resp.data.decode("utf-8"))
    return result


def gateway_call(method: str, **kwargs):
    """
    Make a call to the gateway
    """
    resp = app.test_client().get(
        f"/feeder_gateway/{method}?{'&'.join(f'{key}={value}&' for key, value in kwargs.items())}"
    )
    return json.loads(resp.data.decode("utf-8"))


def get_block_with_transaction(transaction_hash: str) -> dict:
    """
    Retrieve block for given transaction
    """
    transaction = gateway_call("get_transaction", transactionHash=transaction_hash)
    block_number: int = transaction["block_number"]
    block = gateway_call("get_block", blockNumber=block_number)
    return block


def pad_zero(felt: str) -> str:
    """
    Convert felt with format `0xValue` to format `0x0Value`
    """
    felt = felt.lstrip("0x")
    return "0x0" + felt


def test_get_state_update_by_hash(deploy_info, invoke_info, contract_class):
    """
    Get state update for the block
    """
    block_with_deploy = get_block_with_transaction(deploy_info["transaction_hash"])
    block_with_invoke = get_block_with_transaction(invoke_info["transaction_hash"])

    contract_address: str = deploy_info["address"]
    block_with_deploy_hash: str = pad_zero(block_with_deploy["block_hash"])
    block_with_invoke_hash: str = pad_zero(block_with_invoke["block_hash"])
    block_with_deploy_timestamp: int = block_with_deploy["timestamp"]
    block_with_invoke_timestamp: int = block_with_invoke["timestamp"]

    new_root_deploy = "0x0" + gateway_call("get_state_update", blockHash=block_with_deploy_hash)["new_root"].lstrip("0")
    new_root_invoke = "0x0" + gateway_call("get_state_update", blockHash=block_with_invoke_hash)["new_root"].lstrip("0")

    resp = rpc_call(
        "starknet_getStateUpdateByHash", params={
            "block_hash": block_with_deploy_hash
        }
    )
    state_update = resp["result"]

    assert state_update["block_hash"] == block_with_deploy_hash
    assert state_update["new_root"] == new_root_deploy
    assert "old_root" in state_update
    assert isinstance(state_update["old_root"], str)
    assert state_update["accepted_time"] == block_with_deploy_timestamp
    assert state_update["state_diff"] == {
        "storage_diffs": [],
        "contracts": [
            {
                "address": contract_address,
                "contract_hash": pad_zero(hex(compute_class_hash(contract_class))),
            }
        ],
        "nonces": [],
    }

    storage = gateway_call("get_storage_at", contractAddress=contract_address, key=get_storage_var_address("balance"))
    resp = rpc_call(
        "starknet_getStateUpdateByHash", params={
            "block_hash": block_with_invoke_hash
        }
    )
    state_update = resp["result"]

    assert state_update["block_hash"] == block_with_invoke_hash
    assert state_update["new_root"] == new_root_invoke
    assert "old_root" in state_update
    assert isinstance(state_update["old_root"], str)
    assert state_update["accepted_time"] == block_with_invoke_timestamp
    assert state_update["state_diff"] == {
        "storage_diffs": [
            {
                "address": contract_address,
                "key": pad_zero(hex(get_storage_var_address("balance"))),
                "value": storage,
            }
        ],
        "contracts": [],
        "nonces": [],
    }


def test_get_code(deploy_info):
    """
    Get contract code
    """
    contract_address: str = deploy_info["address"]
    contract: dict = gateway_call(
        "get_code", contractAddress=contract_address
    )

    resp = rpc_call(
        "starknet_getCode", params={"contract_address": contract_address}
    )
    code = resp["result"]

    assert code["bytecode"] == contract["bytecode"]
    assert json.loads(code["abi"]) == contract["abi"]


def test_get_code_raises_on_incorrect_contract(deploy_info):
    """
    Get contract code by incorrect contract address
    """
    ex = rpc_call(
        "starknet_getCode", params={"contract_address": "0x0"}
    )

    assert ex["error"] == {
        "code": 20,
        "message": "Contract not found"
    }


def test_chain_id(deploy_info):
    """
    Test chain id
    """
    chain_id = DEFAULT_GENERAL_CONFIG.chain_id.value

    resp = rpc_call("starknet_chainId", params={})
    rpc_chain_id = resp["result"]

    assert isinstance(rpc_chain_id, str)
    assert rpc_chain_id == hex(chain_id)


def test_protocol_version(deploy_info):
    """
    Test protocol version
    """
    protocol_version = "0.15.0"

    resp = rpc_call("starknet_protocolVersion", params={})
    version_hex: str = resp["result"]
    version_bytes = bytes.fromhex(version_hex.lstrip("0x"))
    version = version_bytes.decode("utf-8")

    assert version == protocol_version
