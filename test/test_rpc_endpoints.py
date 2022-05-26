"""
Tests RPC endpoints.
"""
from __future__ import annotations

import json

import pytest
from starkware.starknet.public.abi import get_storage_var_address, get_selector_from_name

from starknet_devnet.server import app
from starknet_devnet.general_config import DEFAULT_GENERAL_CONFIG

from .util import (
    load_file_content,
)
from .test_endpoints import send_transaction


DEPLOY_CONTENT = load_file_content("deploy.json")
INVOKE_CONTENT = load_file_content("invoke.json")


def rpc_call(method: str, params: dict | list) -> dict:
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


@pytest.fixture(name="deploy_info", scope="module")
def fixture_deploy_info() -> dict:
    """
    Deploy a contract on devnet and return deployment info dict
    """
    resp = send_transaction(json.loads(DEPLOY_CONTENT))
    deploy_info = json.loads(resp.data.decode("utf-8"))
    return deploy_info


@pytest.fixture(name="invoke_info", scope="module")
def fixture_invoke_info() -> dict:
    """
    Make an invoke transaction on devnet and return invoke info dict
    """
    invoke_tx = json.loads(INVOKE_CONTENT)
    invoke_tx["calldata"] = ["0"]
    resp = send_transaction(invoke_tx)
    invoke_info = json.loads(resp.data.decode("utf-8"))
    return invoke_info


def pad_zero(felt: str) -> str:
    """
    Convert felt with format `0xValue` to format `0x0Value`
    """
    felt = felt.lstrip("0x")
    return "0x0" + felt


# pylint: disable=unused-argument
def test_get_block_by_number(deploy_info):
    """
    Get block by number
    """
    block_hash: str = gateway_call("get_block", blockNumber=0)["block_hash"]

    resp = rpc_call(
        "starknet_getBlockByNumber", params={"block_number": 0}
    )
    block = resp["result"]
    transaction_hash: str = pad_zero(deploy_info["transaction_hash"])

    assert block["block_hash"] == pad_zero(block_hash)
    assert block["parent_hash"] == "0x0"
    assert block["block_number"] == 0
    assert block["status"] == "ACCEPTED_ON_L2"
    assert block["sequencer"] == hex(DEFAULT_GENERAL_CONFIG.sequencer_address)
    assert block["old_root"] == "0x0"
    assert block["transactions"] == [transaction_hash]


def test_get_block_by_number_raises_on_incorrect_number(deploy_info):
    """
    Get block by incorrect number
    """
    ex = rpc_call(
        "starknet_getBlockByNumber", params={"block_number": 1234}
    )

    assert ex["error"] == {
        "code": 26,
        "message": "Invalid block number"
    }


def test_get_block_by_hash(deploy_info):
    """
    Get block by hash
    """
    block_hash: str = gateway_call("get_block", blockNumber=0)["block_hash"]
    transaction_hash: str = pad_zero(deploy_info["transaction_hash"])

    resp = rpc_call(
        "starknet_getBlockByHash", params={"block_hash": block_hash}
    )
    block = resp["result"]

    assert block["block_hash"] == pad_zero(block_hash)
    assert block["parent_hash"] == "0x0"
    assert block["block_number"] == 0
    assert block["status"] == "ACCEPTED_ON_L2"
    assert block["sequencer"] == hex(DEFAULT_GENERAL_CONFIG.sequencer_address)
    assert block["old_root"] == "0x0"
    assert block["transactions"] == [transaction_hash]


def test_get_block_by_hash_full_txn_scope(deploy_info):
    """
    Get block by hash with scope FULL_TXNS
    """
    block_hash: str = gateway_call("get_block", blockNumber=0)["block_hash"]
    transaction_hash: str = pad_zero(deploy_info["transaction_hash"])
    contract_address: str = pad_zero(deploy_info["address"])

    resp = rpc_call(
        "starknet_getBlockByHash",
        params={
            "block_hash": block_hash,
            "requested_scope": "FULL_TXNS"
        }
    )
    block = resp["result"]

    assert block["transactions"] == [{
        "txn_hash": transaction_hash,
        "max_fee": "0x0",
        "contract_address": contract_address,
        "calldata": None,
        "entry_point_selector": None,
    }]


def test_get_block_by_hash_full_txn_and_receipts_scope(deploy_info):
    """
    Get block by hash with scope FULL_TXN_AND_RECEIPTS
    """
    block_hash: str = gateway_call("get_block", blockNumber=0)["block_hash"]
    transaction_hash: str = pad_zero(deploy_info["transaction_hash"])
    contract_address: str = pad_zero(deploy_info["address"])

    resp = rpc_call(
        "starknet_getBlockByHash",
        params={
            "block_hash": block_hash,
            "requested_scope": "FULL_TXN_AND_RECEIPTS"
        }
    )
    block = resp["result"]

    assert block["transactions"] == [{
        "txn_hash": transaction_hash,
        "max_fee": "0x0",
        "contract_address": contract_address,
        "calldata": None,
        "entry_point_selector": None,
        "actual_fee": "0x0",
        "status": "ACCEPTED_ON_L2",
        "statusData": "",
        "messages_sent": [],
        "l1_origin_message": None,
        "events": []
    }]


def test_get_block_by_hash_raises_on_incorrect_hash(deploy_info):
    """
    Get block by incorrect hash
    """
    ex = rpc_call(
        "starknet_getBlockByHash", params={"block_hash": "0x0"}
    )

    assert ex["error"] == {
        "code": 24,
        "message": "Invalid block hash"
    }


@pytest.mark.xfail
def test_get_state_update_by_hash(deploy_info, invoke_info):
    """
    Get state update for the block
    """
    block_with_deploy = gateway_call("get_block", blockNumber=0)
    block_with_invoke = gateway_call("get_block", blockNumber=1)

    contract_address: str = deploy_info["address"]
    block_with_deploy_hash: str = block_with_deploy["block_hash"]
    block_with_invoke_hash: str = block_with_invoke["block_hash"]

    resp = rpc_call(
        "starknet_getStateUpdateByHash", params={
            "block_hash": block_with_deploy_hash
        }
    )
    state_update = resp["result"]

    assert state_update["block_hash"] == block_with_deploy_hash
    assert "new_root" in state_update
    assert isinstance(state_update["new_root"], str)
    assert "old_root" in state_update
    assert isinstance(state_update["old_root"], str)
    assert "accepted_time" in state_update
    assert isinstance(state_update["accepted_time"], int)
    assert state_update["state_diff"] == {
        "storage_diffs": [],
        "contracts": [
            {
                "address": contract_address,
                "contract_hash": "06f8d704f5a8f6bcb53a1c87c6f8d466ab0aaa5cf962084ac03a2145aac2d823",  # FIXME this is hardcoded but I don't know how this contract
            }                                                                                         #     hash is calculated otherwise
        ],
    }

    resp = rpc_call(
        "starknet_getStateUpdateByHash", params={
            "block_hash": block_with_invoke_hash
        }
    )
    state_update = resp["result"]

    assert state_update["block_hash"] == block_with_invoke_hash
    assert "new_root" in state_update
    assert isinstance(state_update["new_root"], str)
    assert "old_root" in state_update
    assert isinstance(state_update["old_root"], str)
    assert "accepted_time" in state_update
    assert isinstance(state_update["accepted_time"], int)
    assert state_update["state_diff"] == {
        "storage_diffs": [
            {
                # FIXME this will fail because of bug in devnet
                "address": contract_address,
                "key": pad_zero(hex(get_storage_var_address("balance"))),
                "value": "0x0a",
            }
        ],
        "contracts": [],
    }


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
    block = gateway_call("get_block", blockNumber=0)

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


def test_get_transaction_by_hash_deploy(deploy_info):
    """
    Get transaction by hash
    """
    transaction_hash: str = deploy_info["transaction_hash"]
    contract_address: str = deploy_info["address"]

    resp = rpc_call(
        "starknet_getTransactionByHash", params={"transaction_hash": transaction_hash}
    )
    transaction = resp["result"]

    assert transaction == {
        "txn_hash": pad_zero(transaction_hash),
        "contract_address": contract_address,
        "entry_point_selector": None,
        "calldata": None,
        "max_fee": "0x0"
    }


def test_get_transaction_by_hash_raises_on_incorrect_hash(deploy_info):
    """
    Get transaction by incorrect hash
    """
    ex = rpc_call(
        "starknet_getTransactionByHash", params={"transaction_hash": "0x0"}
    )

    assert ex["error"] == {
        "code": 25,
        "message": "Invalid transaction hash"
    }


def test_get_transaction_by_block_hash_and_index(deploy_info):
    """
    Get transaction by block hash and transaction index
    """
    block = gateway_call("get_block", blockNumber=0)
    transaction_hash: str = deploy_info["transaction_hash"]
    contract_address: str = deploy_info["address"]
    block_hash: str = block["block_hash"]
    index: int = 0

    resp = rpc_call(
        "starknet_getTransactionByBlockHashAndIndex", params={
            "block_hash": block_hash,
            "index": index
        }
    )
    transaction = resp["result"]

    assert transaction == {
        "txn_hash": pad_zero(transaction_hash),
        "contract_address": contract_address,
        "entry_point_selector": None,
        "calldata": None,
        "max_fee": "0x0",
    }


def test_get_transaction_by_block_hash_and_index_raises_on_incorrect_block_hash(deploy_info):
    """
    Get transaction by incorrect block hash
    """
    ex = rpc_call(
        "starknet_getTransactionByBlockHashAndIndex", params={
            "block_hash": "0x0",
            "index": 0
        }
    )

    assert ex["error"] == {
        "code": 24,
        "message": "Invalid block hash"
    }


def test_get_transaction_by_block_hash_and_index_raises_on_incorrect_index(deploy_info):
    """
    Get transaction by block hash and incorrect transaction index
    """
    block = gateway_call("get_block", blockNumber=0)
    block_hash: str = block["block_hash"]

    ex = rpc_call(
        "starknet_getTransactionByBlockHashAndIndex", params={
            "block_hash": block_hash,
            "index": 999999
        }
    )

    assert ex["error"] == {
        "code": 27,
        "message": "Invalid transaction index in a block"
    }


def test_get_transaction_by_block_number_and_index(deploy_info):
    """
    Get transaction by block number and transaction index
    """
    transaction_hash: str = deploy_info["transaction_hash"]
    contract_address: str = deploy_info["address"]
    block_number: int = 0
    index: int = 0

    resp = rpc_call(
        "starknet_getTransactionByBlockNumberAndIndex", params={
            "block_number": block_number,
            "index": index
        }
    )
    transaction = resp["result"]

    assert transaction == {
        "txn_hash": pad_zero(transaction_hash),
        "contract_address": contract_address,
        "entry_point_selector": None,
        "calldata": None,
        "max_fee": "0x0",
    }


def test_get_transaction_by_block_number_and_index_raises_on_incorrect_block_number(deploy_info):
    """
    Get transaction by incorrect block number
    """
    ex = rpc_call(
        "starknet_getTransactionByBlockNumberAndIndex", params={
            "block_number": 99999,
            "index": 0
        }
    )

    assert ex["error"] == {
        "code": 26,
        "message": "Invalid block number"
    }


def test_get_transaction_by_block_number_and_index_raises_on_incorrect_index(deploy_info):
    """
    Get transaction by block hash and incorrect transaction index
    """
    block_number: int = 0

    ex = rpc_call(
        "starknet_getTransactionByBlockNumberAndIndex", params={
            "block_number": block_number,
            "index": 99999
        }
    )

    assert ex["error"] == {
        "code": 27,
        "message": "Invalid transaction index in a block"
    }


def test_get_transaction_receipt(deploy_info, invoke_info):
    """
    Get transaction receipt
    """
    transaction_hash: str = deploy_info["transaction_hash"]

    resp = rpc_call(
        "starknet_getTransactionReceipt", params={
            "transaction_hash": transaction_hash
        }
    )
    receipt = resp["result"]

    assert receipt == {
        "txn_hash": pad_zero(transaction_hash),
        "status": "ACCEPTED_ON_L2",
        "statusData": "",
        "messages_sent": [],
        "l1_origin_message": None,
        "events": [],
        "actual_fee": "0x0"
    }


def test_get_transaction_receipt_on_incorrect_hash(deploy_info):
    """
    Get transaction receipt by incorrect hash
    """
    ex = rpc_call(
        "starknet_getTransactionReceipt", params={
            "transaction_hash": "0x0"
        }
    )

    assert ex["error"] == {
        "code": 25,
        "message": "Invalid transaction hash"
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


def test_get_block_transaction_count_by_hash(deploy_info):
    """
    Get count of transactions in block by block hash
    """
    block = gateway_call("get_block", blockNumber=0)
    block_hash: str = block["block_hash"]

    resp = rpc_call(
        "starknet_getBlockTransactionCountByHash", params={"block_hash": block_hash}
    )
    count = resp["result"]

    assert count == 1


def test_get_block_transaction_count_by_hash_raises_on_incorrect_hash(deploy_info):
    """
    Get count of transactions in block by incorrect block hash
    """
    ex = rpc_call(
        "starknet_getBlockTransactionCountByHash", params={"block_hash": "0x0"}
    )

    assert ex["error"] == {
        "code": 24,
        "message": "Invalid block hash"
    }


def test_get_block_transaction_count_by_number(deploy_info):
    """
    Get count of transactions in block by block number
    """
    block_number: int = 0

    resp = rpc_call(
        "starknet_getBlockTransactionCountByNumber", params={"block_number": block_number}
    )
    count = resp["result"]

    assert count == 1


def test_get_block_transaction_count_by_number_raises_on_incorrect_number(deploy_info):
    """
    Get count of transactions in block by incorrect block number
    """
    ex = rpc_call(
        "starknet_getBlockTransactionCountByNumber", params={"block_number": 99999}
    )

    assert ex["error"] == {
        "code": 26,
        "message": "Invalid block number"
    }


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


def test_get_block_number(deploy_info):
    """
    Get the number of the latest accepted  block
    """

    latest_block = gateway_call("get_block", blockNumber="latest")
    latest_block_number: int = latest_block["block_number"]

    resp = rpc_call(
        "starknet_blockNumber", params={}
    )
    block_number: int = resp["result"]

    assert latest_block_number == block_number


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
    protocol_version = "0.8.0"

    resp = rpc_call("starknet_protocolVersion", params={})
    version_hex: str = resp["result"]
    version_bytes = bytes.fromhex(version_hex.lstrip("0x"))
    version = version_bytes.decode("utf-8")

    assert version == protocol_version
