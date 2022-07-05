"""
Tests RPC endpoints.
"""
# pylint: disable=too-many-lines
from __future__ import annotations

import json
import typing
from typing import List, Union

import pytest
from starkware.starknet.public.abi import get_storage_var_address, get_selector_from_name
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.services.api.gateway.transaction import Transaction, Deploy

from starknet_devnet.server import app
from starknet_devnet.general_config import DEFAULT_GENERAL_CONFIG

from .util import load_file_content
from .test_endpoints import send_transaction


DEPLOY_CONTENT = load_file_content("deploy_rpc.json")
INVOKE_CONTENT = load_file_content("invoke_rpc.json")
DECLARE_CONTENT = load_file_content("declare.json")


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


@pytest.fixture(name="contract_class")
def fixture_contract_class() -> ContractClass:
    """
    Make ContractDefinition from deployment transaction used in tests
    """
    transaction: Deploy = typing.cast(Deploy, Transaction.loads(DEPLOY_CONTENT))
    return transaction.contract_definition


@pytest.fixture(name="class_hash")
def fixture_class_hash(deploy_info) -> str:
    """
    Class hash of deployed contract
    """
    class_hash = gateway_call("get_class_hash_at", contractAddress=deploy_info["address"])
    return class_hash


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
    return {**invoke_info, **invoke_tx}


@pytest.fixture(name="declare_info", scope="module")
def fixture_declare_info() -> dict:
    """
    Make a declare transaction on devnet and return declare info dict
    """
    declare_tx = json.loads(DECLARE_CONTENT)
    resp = send_transaction(declare_tx)
    declare_info = json.loads(resp.data.decode("utf-8"))
    return {**declare_info, **declare_tx}


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


# pylint: disable=unused-argument
def test_get_block_by_number(deploy_info):
    """
    Get block by number
    """
    gateway_block: dict = get_block_with_transaction(deploy_info["transaction_hash"])
    block_hash: str = gateway_block["block_hash"]
    block_number: int = gateway_block["block_number"]
    new_root: str = gateway_block["state_root"]

    resp = rpc_call(
        "starknet_getBlockByNumber", params={"block_number": block_number}
    )
    block = resp["result"]
    transaction_hash: str = pad_zero(deploy_info["transaction_hash"])

    assert block["block_hash"] == pad_zero(block_hash)
    assert block["parent_hash"] == pad_zero(gateway_block["parent_block_hash"])
    assert block["block_number"] == block_number
    assert block["status"] == "ACCEPTED_ON_L2"
    assert block["sequencer_address"] == hex(DEFAULT_GENERAL_CONFIG.sequencer_address)
    assert block["new_root"] == pad_zero(new_root)
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
    gateway_block: dict = get_block_with_transaction(deploy_info["transaction_hash"])
    block_hash: str = gateway_block["block_hash"]
    new_root: str = gateway_block["state_root"]
    transaction_hash: str = pad_zero(deploy_info["transaction_hash"])

    resp = rpc_call(
        "starknet_getBlockByHash", params={"block_hash": block_hash}
    )
    block = resp["result"]

    assert block["block_hash"] == pad_zero(block_hash)
    assert block["parent_hash"] == pad_zero(gateway_block["parent_block_hash"])
    assert block["block_number"] == gateway_block["block_number"]
    assert block["status"] == "ACCEPTED_ON_L2"
    assert block["sequencer_address"] == hex(DEFAULT_GENERAL_CONFIG.sequencer_address)
    assert block["new_root"] == pad_zero(new_root)
    assert block["transactions"] == [transaction_hash]


def test_get_block_by_hash_full_txn_scope(deploy_info):
    """
    Get block by hash with scope FULL_TXNS
    """
    block_hash: str = get_block_with_transaction(deploy_info["transaction_hash"])["block_hash"]
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
        "calldata": [],
        "entry_point_selector": None,
        "signature": [],
        "version": "0x0"
    }]


def test_get_block_by_hash_full_txn_and_receipts_scope(deploy_info):
    """
    Get block by hash with scope FULL_TXN_AND_RECEIPTS
    """
    block_hash: str = get_block_with_transaction(deploy_info["transaction_hash"])["block_hash"]
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
        "calldata": [],
        "entry_point_selector": None,
        "signature": [],
        "version": "0x0",
        "actual_fee": "0x0",
        "status": "ACCEPTED_ON_L2",
        "statusData": None,
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
        "max_fee": "0x0",
        "calldata": [],
        "entry_point_selector": None,
        "signature": [],
        "version": "0x0"
    }


def test_get_transaction_by_hash_invoke(invoke_info):
    """
    Get transaction by hash
    """
    transaction_hash: str = invoke_info["transaction_hash"]
    contract_address: str = invoke_info["address"]
    entry_point_selector: str = invoke_info["entry_point_selector"]
    signature: List[str] = [pad_zero(hex(int(sig))) for sig in invoke_info["signature"]]
    calldata: List[str] = [pad_zero(hex(int(data))) for data in invoke_info["calldata"]]

    resp = rpc_call(
        "starknet_getTransactionByHash", params={"transaction_hash": transaction_hash}
    )
    transaction = resp["result"]

    assert transaction == {
        "txn_hash": pad_zero(transaction_hash),
        "contract_address": contract_address,
        "max_fee": "0x0",
        "calldata": calldata,
        "entry_point_selector": pad_zero(entry_point_selector),
        "signature": signature,
        "version": "0x0"
    }


def test_get_transaction_by_hash_declare(declare_info):
    """
    Get transaction by hash
    """
    transaction_hash: str = declare_info["transaction_hash"]
    signature: List[str] = [pad_zero(hex(int(sig))) for sig in declare_info["signature"]]
    sender_address: str = declare_info["sender_address"]

    resp = rpc_call(
        "starknet_getTransactionByHash", params={"transaction_hash": transaction_hash}
    )
    transaction = resp["result"]

    assert transaction["txn_hash"] == pad_zero(transaction_hash)
    assert transaction["max_fee"] == "0x0"
    assert transaction["signature"] == signature
    assert transaction["version"] == "0x0"
    assert transaction["sender_address"] == pad_zero(sender_address)
    assert transaction["contract_class"]["entry_points_by_type"] == {
        "CONSTRUCTOR": [],
        "EXTERNAL": [
            {
                "offset": pad_zero("0x3a"),
                "selector": pad_zero("0x362398bec32bc0ebb411203221a35a0301193a96f317ebe5e40be9f60d15320")
            },
            {
                "offset": pad_zero("0x5b"),
                "selector": pad_zero("0x39e11d48192e4333233c7eb19d10ad67c362bb28580c604d67884c85da39695")
            }
        ],
        "L1_HANDLER": []
    }
    assert transaction["contract_class"]["program"] != ""


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
    block = get_block_with_transaction(deploy_info["transaction_hash"])
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
        "max_fee": "0x0",
        "calldata": [],
        "entry_point_selector": None,
        "signature": [],
        "version": "0x0"
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
    block = get_block_with_transaction(deploy_info["transaction_hash"])
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
    block = get_block_with_transaction(transaction_hash)
    block_number: int = block["block_number"]
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
        "max_fee": "0x0",
        "calldata": [],
        "entry_point_selector": None,
        "signature": [],
        "version": "0x0"
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


def test_get_deploy_transaction_receipt(deploy_info):
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
        "statusData": None,
        "actual_fee": "0x0"
    }


def test_get_declare_transaction_receipt(declare_info):
    """
    Get transaction receipt
    """
    transaction_hash: str = declare_info["transaction_hash"]

    resp = rpc_call(
        "starknet_getTransactionReceipt", params={
            "transaction_hash": transaction_hash
        }
    )
    receipt = resp["result"]

    assert receipt == {
        "txn_hash": pad_zero(transaction_hash),
        "status": "ACCEPTED_ON_L2",
        "statusData": None,
        "actual_fee": "0x0"
    }


def test_get_invoke_transaction_receipt(invoke_info):
    """
    Get transaction receipt
    """
    transaction_hash: str = invoke_info["transaction_hash"]

    resp = rpc_call(
        "starknet_getTransactionReceipt", params={
            "transaction_hash": transaction_hash
        }
    )
    receipt = resp["result"]

    # Standard == receipt dict test cannot be done here, because invoke transaction fails since no contracts
    # are actually deployed on devnet, when running test without @devnet_in_background
    assert receipt["txn_hash"] == pad_zero(transaction_hash)
    assert receipt["actual_fee"] == "0x0"
    assert receipt["l1_origin_message"] is None
    assert receipt["events"] == []
    assert receipt["messages_sent"] == []


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
    block = get_block_with_transaction(deploy_info["transaction_hash"])
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
    protocol_version = "0.15.0"

    resp = rpc_call("starknet_protocolVersion", params={})
    version_hex: str = resp["result"]
    version_bytes = bytes.fromhex(version_hex.lstrip("0x"))
    version = version_bytes.decode("utf-8")

    assert version == protocol_version


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
