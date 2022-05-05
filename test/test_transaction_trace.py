"""
Test get_transaction endpoint
"""

import pytest
import requests

from .util import deploy, invoke, load_json_from_path, devnet_in_background
from .settings import FEEDER_GATEWAY_URL
from .shared import ABI_PATH, CONTRACT_PATH, SIGNATURE, NONEXISTENT_TX_HASH

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

def assert_function_invocation(function_invocation, expected_path):
    """Asserts function invocation"""
    expected_function_invocation = load_json_from_path(expected_path)
    assert function_invocation == expected_function_invocation

@pytest.mark.transaction_trace
@devnet_in_background()
def test_deploy_transaction_trace():
    """Test deploy transaction trace"""
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
@devnet_in_background()
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
@devnet_in_background()
def test_invoke_transaction_hash_with_signature():
    """Test invoke transaction trace with signature"""
    contract_address = deploy_empty_contract()["address"]
    tx_hash = invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH, SIGNATURE)
    res = get_transaction_trace_response(tx_hash)

    assert res.status_code == 200

    transaction_trace = res.json()

    expected_signature = [hex(int(s)) for s in SIGNATURE]
    assert transaction_trace["signature"] == expected_signature

    assert_function_invocation(
        transaction_trace["function_invocation"],
        "test/expected/invoke_function_invocation.json"
    )

@pytest.mark.transaction_trace
@devnet_in_background()
def test_nonexistent_transaction_hash():
    """Test if it throws 500 for nonexistent transaction trace"""
    res = get_transaction_trace_response(NONEXISTENT_TX_HASH)

    assert res.status_code == 500
