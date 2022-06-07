"""
Test endpoints directly.
"""

from test.util import load_file_content
from test.settings import FEEDER_GATEWAY_URL, GATEWAY_URL

import json
import requests
import pytest

from starknet_devnet.server import app
from .util import devnet_in_background, load_file_content

DEPLOY_CONTENT = load_file_content("deploy.json")
INVOKE_CONTENT = load_file_content("invoke.json")
CALL_CONTENT = load_file_content("call.json")
INVALID_HASH = "0x58d4d4ed7580a7a98ab608883ec9fe722424ce52c19f2f369eeea301f535914"

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

def assert_deploy_resp(resp: bytes):
    """Asserts the validity of deploy response body."""
    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert set(resp_dict.keys()) == set(["address", "code", "transaction_hash"])
    assert resp_dict["code"] == "TRANSACTION_RECEIVED"

def assert_invoke_resp(resp: bytes):
    """Asserts the validity of invoke response body."""
    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert set(resp_dict.keys()) == set(["address", "code", "transaction_hash", "result"])
    assert resp_dict["code"] == "TRANSACTION_RECEIVED"
    assert resp_dict["result"] == []

def assert_call_resp(resp: bytes):
    """Asserts the validity of call response body."""
    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert resp_dict == { "result": ["0xa"] }

@pytest.mark.deploy
def test_deploy_without_calldata():
    """Deploy with complete request data"""
    req_dict = json.loads(DEPLOY_CONTENT)
    del req_dict["constructor_calldata"]
    resp = send_transaction(req_dict)
    assert resp.status_code == 400

@pytest.mark.deploy
def test_deploy_with_complete_request_data():
    """Deploy without calldata"""
    resp = app.test_client().post(
        "/gateway/add_transaction",
        content_type="application/json",
        data=DEPLOY_CONTENT
    )
    assert_deploy_resp(resp)

@pytest.mark.invoke
def test_invoke_without_signature():
    """Invoke without signature"""
    req_dict = json.loads(INVOKE_CONTENT)
    del req_dict["signature"]
    resp = send_transaction(req_dict)
    assert resp.status_code == 400

@pytest.mark.invoke
def test_invoke_without_calldata():
    """Invoke without calldata"""
    req_dict = json.loads(INVOKE_CONTENT)
    del req_dict["calldata"]
    resp = send_transaction(req_dict)
    assert resp.status_code == 400

@pytest.mark.invoke
def test_invoke_with_complete_request_data():
    """Invoke with complete request data"""
    req_dict = json.loads(INVOKE_CONTENT)
    resp = send_transaction(req_dict)
    assert_invoke_resp(resp)

@pytest.mark.call
def test_call_without_signature():
    """Call without signature"""
    req_dict = json.loads(CALL_CONTENT)
    del req_dict["signature"]
    resp = send_call(req_dict)
    assert resp.status_code == 400

@pytest.mark.call
def test_call_without_calldata():
    """Call without calldata"""
    req_dict = json.loads(CALL_CONTENT)
    del req_dict["calldata"]
    resp = send_call(req_dict)
    assert resp.status_code == 400

@pytest.mark.call
def test_call_with_complete_request_data():
    """Call with complete request data"""
    req_dict = json.loads(CALL_CONTENT)
    resp = send_call(req_dict)
    assert_call_resp(resp)

# Error response tests
def send_transaction_with_requests(req_dict: dict):
    """Sends the dict in a POST request and returns the response data."""
    return requests.post(
        f"{GATEWAY_URL}/add_transaction",
        json=json.dumps(req_dict)
    )

def send_call_with_requests(req_dict: dict):
    """Sends the call dict in a POST request and returns the response data."""
    return requests.post(
        f"{FEEDER_GATEWAY_URL}/call_contract",
        json=json.dumps(req_dict)
    )

def get_block_number(req_dict: dict):
    """Get block number from request dict"""
    block_number = req_dict["blockNumber"]
    return requests.get(
        f"{FEEDER_GATEWAY_URL}/get_block?blockNumber={block_number}"
    )

def get_transaction_trace(transaction_hash:str):
    """Get transaction trace from request dict"""
    # transactionHash
    return requests.get(
        f"{FEEDER_GATEWAY_URL}/get_transaction_trace?transactionHash={transaction_hash}"
    )

def get_full_contract(contract_adress):
    """Get full contract class of a contract at a specific address"""
    return requests.get(
        f"{FEEDER_GATEWAY_URL}/get_full_contract?contractAddress={contract_adress}"
    )

def get_class_by_hash(class_hash: str):
    """Get contract class by class hash"""
    return requests.get(
        f"{FEEDER_GATEWAY_URL}/get_class_by_hash?classHash={class_hash}"
    )

def get_class_hash_at(contract_address: str):
    """Get class hash of a contract at the provided address"""
    return requests.get(
        f"{FEEDER_GATEWAY_URL}/get_class_hash_at?contractAddress={contract_address}"
    )

def get_state_update(block_hash, block_number):
    """Get state update"""
    return requests.get(
        f"{FEEDER_GATEWAY_URL}/get_state_update?blockHash={block_hash}&blockNumber={block_number}"
    )

@devnet_in_background()
def test_error_response_deploy_without_calldata():
    """Deploy with incomplete request data"""
    req_dict = json.loads(DEPLOY_CONTENT)
    del req_dict["constructor_calldata"]
    resp = send_transaction_with_requests(req_dict)

    json_error_message = resp.json()["message"]
    msg = "Invalid tx:"
    assert msg in json_error_message

@devnet_in_background()
def test_error_response_call_without_calldata():
    """Call without calldata"""
    req_dict = json.loads(CALL_CONTENT)
    del req_dict["calldata"]
    resp = send_call_with_requests(req_dict)

    json_error_message = resp.json()["message"]
    assert resp.status_code == 400
    assert json_error_message is not None

@devnet_in_background()
def test_error_response_call_with_negative_block_number():
    """Call with negative block number"""
    resp = get_block_number({"blockNumber": -1})

    json_error_message = resp.json()["message"]
    assert resp.status_code == 500
    assert json_error_message is not None

@devnet_in_background()
def test_error_response_call_with_invalid_transaction_hash():
    """Call with invalid transaction hash"""
    resp = get_transaction_trace(INVALID_HASH)

    json_error_message = resp.json()["message"]
    msg = "Transaction corresponding to hash"
    assert resp.status_code == 500
    assert json_error_message.startswith(msg)

@devnet_in_background()
def test_error_response_call_with_unavailable_contract():
    """Call with unavailable contract"""
    resp = get_full_contract(INVALID_HASH)

    json_error_message = resp.json()["message"]
    assert resp.status_code == 500
    assert json_error_message is not None

@devnet_in_background()
def test_error_response_call_with_state_update():
    """Call with unavailable state update"""
    resp = get_state_update(INVALID_HASH, -1)

    json_error_message = resp.json()["message"]
    assert resp.status_code == 500
    assert json_error_message is not None
