"""
Test JSON error response
"""

import json
import requests
import pytest

from starknet_devnet.server import app
from .settings import GATEWAY_URL
from .util import run_devnet_in_background, load_file_content

DEPLOY_CONTENT = load_file_content("deploy.json")

INVOKE_CONTENT = load_file_content("invoke.json")
CALL_CONTENT = load_file_content("call.json")
INVALID_HASH = "0x58d4d4ed7580a7a98ab608883ec9fe722424ce52c19f2f369eeea301f535914"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Cleanup after tests finish."""

    # before test
    devnet_proc = run_devnet_in_background()

    yield
    # after test
    devnet_proc.kill()

def send_error_request():
    """Send HTTP request to trigger error response."""
    json_body = { "dummy": "dummy_value" }
    return requests.post(f"{GATEWAY_URL}/dump", json=json_body)

def send_transaction(req_dict: dict):
    """Sends the dict in a POST request and returns the response data."""
    return app.test_client().post(
        "/gateway/add_transaction",
        content_type="application/json",
        data=json.dumps(req_dict)
    )

def send_call(req_dict: dict):
    """Sends the call dict in a POST request and returns the response data."""
    return app.test_client().post(
        "/feeder_gateway/call_contract",
        content_type="application/json",
        data=json.dumps(req_dict)
    )

def get_block_number(req_dict: dict):
    """Get block number from request dict"""
    block_number = req_dict["blockNumber"]
    return app.test_client().get(
        f"/feeder_gateway/get_block?blockNumber={block_number}"
    )

def get_transaction_trace(transaction_hash:str):
    """Get transaction trace from request dict"""
    # transactionHash
    return app.test_client().get(
        f"/feeder_gateway/get_transaction_trace?transactionHash={transaction_hash}"
    )

def get_get_full_contract(contract_adress):
    """Get full contract definition of a contract at a specific address"""
    return app.test_client().get(
        f"/feeder_gateway/get_full_contract?contractAddress={contract_adress}"
    )

def get_state_update(block_hash, block_number):
    """Get state update"""
    return app.test_client().get(
        f"/feeder_gateway/get_state_update?blockHash={block_hash}&blockNumber={block_number}"
    )

def estimate_fee(req_dict: dict):
    """Estimate fee of a given transaction"""
    return app.test_client().post(
        "/feeder_gateway/estimate_fee",
        content_type="application/json",
        data=json.dumps(req_dict)
    )

def load_l1_messaging_contract(req_dict: dict):
    """Load L1 messaging contract"""
    return app.test_client().post(
        "/postman/load_l1_messaging_contract",
        content_type="application/json",
        data=json.dumps(req_dict)
    )

def test_error_response_code():
    """Assert response status code is expected."""
    resp = send_error_request()

    assert resp.status_code == 400

def test_error_response_message():
    """Assert response message is expected."""
    resp = send_error_request()

    data = resp.json()
    msg = "No path provided"
    assert data["error"] == msg

def test_error_response_deploy_without_calldata():
    """Deploy with complete request data"""
    req_dict = json.loads(DEPLOY_CONTENT)
    del req_dict["constructor_calldata"]
    resp = send_transaction(req_dict)

    json_error_message = json.loads(resp.data)["error"]
    msg = "Invalid tx:"
    assert json_error_message.startswith(msg)

def test_error_response_call_without_calldata():
    """Call without calldata"""
    req_dict = json.loads(CALL_CONTENT)
    del req_dict["calldata"]
    resp = send_call(req_dict)

    json_error_message = json.loads(resp.data)["error"]
    assert resp.status_code == 400
    assert json_error_message is not None

def test_error_response_call_with_negative_block_number():
    """Call with negative block number"""
    resp = get_block_number({"blockNumber": -1})

    json_error_message = json.loads(resp.data)["error"]
    assert resp.status_code == 500
    assert json_error_message is not None

def test_error_response_call_with_invalid_transaction_hash():
    """Call with invalid transaction hash"""
    resp = get_transaction_trace(INVALID_HASH)

    json_error_message = json.loads(resp.data)["error"]
    msg = "Transaction corresponding to hash"
    assert resp.status_code == 500
    assert json_error_message.startswith(msg)

def test_error_response_call_with_unavailable_contract():
    """Call with unavailable contract"""
    resp = get_get_full_contract(INVALID_HASH)

    json_error_message = json.loads(resp.data)["error"]
    assert resp.status_code == 500
    assert json_error_message is not None

def test_error_response_call_with_state_update():
    """Call with unavailable state update"""
    resp = get_state_update(INVALID_HASH, -1)

    json_error_message = json.loads(resp.data)["error"]
    assert resp.status_code == 500
    assert json_error_message is not None

def test_error_response_call_estimate_fee_in_unknown_address():
    """Call with unknown invoke function"""
    req_dict = json.loads(INVOKE_CONTENT)
    del req_dict["type"]
    resp = estimate_fee(req_dict)

    json_error_message = json.loads(resp.data)["error"]
    msg = "Contract with address"
    assert resp.status_code == 500
    assert json_error_message.startswith(msg)

def test_error_response_call_estimate_fee_with_invalid_data():
    """Call estimate fee with invalid data on body"""
    req_dict = json.loads(DEPLOY_CONTENT)
    resp = estimate_fee(req_dict)

    json_error_message = json.loads(resp.data)["error"]
    msg = "Invalid tx:"
    assert resp.status_code == 400
    assert json_error_message.startswith(msg)

def test_error_response_call_invalid_starknet_function_call_load_l1_messaging_contract():
    """Call with invalid data on starknet function call"""
    load_messaging_contract_request = {}
    resp = load_l1_messaging_contract(load_messaging_contract_request)

    json_error_message = json.loads(resp.data)["error"]
    msg = "L1 network or StarknetMessaging contract address not specified"
    assert resp.status_code == 400
    assert json_error_message == msg
