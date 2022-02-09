"""
Test endpoints directly.
"""

import json
import os
import subprocess
import pytest

from starknet_devnet.server import app
from test.settings import GANACHE_URL

deploy_messaging_contract_request: dict
load_messaging_contract_request: dict

def load_file_content(file_name: str):
    """Load content of file located in the same directory as this test file."""
    full_file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(full_file_path, encoding="utf-8") as deploy_file:
        return deploy_file.read()

def init_ganache():
    """Initializes a new Ganache instance"""
    args = "ganache-cli -p 5005 --chainId 32 --networkId 32 --gasLimit 8000000 --allow-unlimited-contract-size &"
    subprocess.run(args, encoding="utf-8", check=False, capture_output=True)

def deploy_messaging_contract():
    """Deploys a new Mock Messaging contract in the Ganache instance"""
    
    deploy_messaging_contract_request["networkUrl"] = GANACHE_URL

    resp = app.test_client().post(
        "/postman/deploy_l1_messaging_contract",
        content_type="application/json",
        data=json.dumps(deploy_messaging_contract_request)
    )

    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert "address" in resp_dict
    assert resp_dict["l1_provider"] == GANACHE_URL




def deploy_l1_contracts():
    """Deploys Ethereum contracts in the Ganache instance, including the L1L2Example and MockStarknetMessaging contracts"""

    args = "( cd test && truffle migrate)"
    output = subprocess.run(args, encoding="utf-8", check=False, capture_output=True)
    assert output.returncode == 0
    
    messaging_contract = json.loads(load_file_content("/build/contracts/MockStarknetMessaging.json"))
    l1l2_example_contract = json.loads(load_file_content("/build/contracts/L1L2Example.json"))

    messaging_contract_address = messaging_contract["networks"]["32"]["address"]
    l1l2_example_contract_address = l1l2_example_contract["networks"]["32"]["address"]

def load_messaging_contract():
    """Loads a Mock Messaging contract already deployed in the Ganache instance"""

    load_messaging_contract_request["networkUrl"] = GANACHE_URL
    load_messaging_contract_request["address"] = messaging_contract_address

    resp = app.test_client().post(
        "/postman/deploy_l1_messaging_contract",
        content_type="application/json",
        data=json.dumps(load_messaging_contract_request)
    )

    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert resp_dict["address"] == messaging_contract_address
    assert resp_dict["l1_provider"] == GANACHE_URL







def send_call(req_dict: dict):
    """Sends the call dict in a POST request and returns the response data."""
    return app.test_client().post(
        "/feeder_gateway/call_contract",
        content_type="application/json",
        data=json.dumps(req_dict)
    )

def assert_deploy_resp(resp: bytes):
    """Asserts the validity of invoke response body."""
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
