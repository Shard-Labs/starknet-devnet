"""
Test get_transaction endpoint
"""

import pytest
import requests

from starkware.starknet.core.os.contract_hash import compute_contract_hash

from .util import deploy, load_contract_definition, run_devnet_in_background, invoke, load_json_from_path
from .settings import FEEDER_GATEWAY_URL

ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract.json"
ABI_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract_abi.json"
BALANCE_KEY = "916907772491729262376534102982219947830828984996257231353398618781993312401"
SIGNATURE = [
    "1225578735933442828068102633747590437426782890965066746429241472187377583468",
    "3568809569741913715045370357918125425757114920266578211811626257903121825123"
]

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background()

    yield

    # after test
    devnet_proc.kill()

def get_transaction_trace_response(tx_hash=None):
    """Get transaction trace response"""
    params = {
        "transactionHash": tx_hash,
    }

    res = requests.get(
        f"{FEEDER_GATEWAY_URL}/feeder_gateway/get_transaction_trace",
        params=params
    )

    return res

def deploy_empty_contract():
    """
    Deploy sample contract with balance = 0.
    Returns transaction hash.
    """
    return deploy(CONTRACT_PATH, inputs=["0"], salt="0x99")

def get_contract_hash():
    """Get contract hash of the sample contract"""
    contract_definition = load_contract_definition(CONTRACT_PATH)

    return compute_contract_hash(contract_definition)

def assert_function_invocation(function_invocation, expected_path):
    """Asserts function invocation"""
    expected_function_invocation = load_json_from_path(expected_path)

    assert function_invocation == expected_function_invocation


@pytest.mark.transaction_trace
def test_deploy_transaction_trace():
    """Test deploy transaction race"""
    tx_hash = deploy_empty_contract()["tx_hash"]
    res = get_transaction_trace_response(tx_hash)

    assert res.status_code == 200

    transaction_trace = res.json()
    assert transaction_trace["signature"] == []
    assert_function_invocation(
        transaction_trace["function_invocation"],
        "test/expected/deploy_function_invocation.json"
    )

@pytest.mark.transaction_trace
def test_invoke_transaction_hash():
    """Test invoke transaction trace"""
    contract_address = deploy_empty_contract()["address"]
    tx_hash = invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH)
    res = get_transaction_trace_response(tx_hash)

    assert res.status_code == 200

    transaction_trace = res.json()
    assert transaction_trace["signature"] == []
    assert_function_invocation(
        transaction_trace["function_invocation"],
        "test/expected/invoke_function_invocation.json"
    )


@pytest.mark.transaction_trace
def test_invoke_transaction_hash_with_signature():
    """Test invoke transaction trace with signature"""
    contract_address = deploy_empty_contract()["address"]
    tx_hash = invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH, SIGNATURE)
    res = get_transaction_trace_response(tx_hash)

    assert res.status_code == 200

    transaction_trace = res.json()
    assert transaction_trace["signature"] == SIGNATURE
    assert_function_invocation(
        transaction_trace["function_invocation"],
        "test/expected/invoke_function_invocation.json"
    )

@pytest.mark.transaction_trace
def test_nonexistent_transaction_hash():
    """Test if it throws 500 for nonexistent transaction trace"""
    tx_hash = "0x0"
    res = get_transaction_trace_response(tx_hash)

    assert res.status_code == 500
