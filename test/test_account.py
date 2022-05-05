"""
Test account functionality.
"""
from test.settings import GATEWAY_URL

import json
import requests
import pytest

from .shared import ABI_PATH, CONTRACT_PATH
from .util import (
    assert_tx_status,
    deploy,
    devnet_in_background,
    load_file_content,
    call,
    estimate_fee
)
from .account import (
    ACCOUNT_ABI_PATH,
    PUBLIC_KEY,
    deploy_account_contract,
    get_nonce,
    execute,
    get_estimated_fee
)

INVOKE_CONTENT = load_file_content("invoke.json")
DEPLOY_CONTENT = load_file_content("deploy.json")
ACCOUNT_ADDRESS = "0x066a91d591d5ba09d37f21fd526242c1ddc6dc6b0ce72b2482a4c6c033114e3a"
INVALID_HASH = "0x58d4d4ed7580a7a98ab608883ec9fe722424ce52c19f2f369eeea301f535914"
SALT = "0x99"

def deploy_empty_contract():
    """Deploy sample contract with balance = 0."""
    return deploy(CONTRACT_PATH, inputs=["0"], salt=SALT)

@pytest.mark.account
@devnet_in_background()
def test_account_contract_deploy():
    """Test account contract deploy, public key and initial nonce value."""
    deploy_info = deploy_account_contract(salt=SALT)
    assert deploy_info["address"] == ACCOUNT_ADDRESS

    deployed_public_key = call(
        "get_public_key", ACCOUNT_ADDRESS, ACCOUNT_ABI_PATH
    )
    assert int(deployed_public_key, 16) == PUBLIC_KEY

    nonce = get_nonce(ACCOUNT_ADDRESS)
    assert nonce == "0"

@pytest.mark.account
@devnet_in_background()
def test_invoke_another_contract():
    """Test invoking another contract."""
    deploy_info = deploy_empty_contract()
    deploy_account_contract(salt=SALT)
    to_address = int(deploy_info["address"], 16)

    # execute increase_balance call
    calls = [(to_address, "increase_balance", [10, 20])]
    tx_hash = execute(calls, ACCOUNT_ADDRESS)

    assert_tx_status(tx_hash, "ACCEPTED_ON_L2")

    # check if nonce is increased
    nonce = get_nonce(ACCOUNT_ADDRESS)
    assert nonce == "1"

    # check if balance is increased
    balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)
    assert balance == "30"

@pytest.mark.account
@devnet_in_background()
def test_estimated_fee():
    """Test estimate fees."""
    deploy_info = deploy_empty_contract()
    deploy_account_contract(salt=SALT)
    to_address = int(deploy_info["address"], 16)

    initial_balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)

    # get estimated fee for increase_balance call
    calls = [(to_address, "increase_balance", [10, 20])]
    estimated_fee = get_estimated_fee(calls, ACCOUNT_ADDRESS)

    assert estimated_fee > 0

    # estimate fee without account
    estimated_fee_without_account = estimate_fee(
        "increase_balance",
        ["10", "20"],
        deploy_info["address"],
        ABI_PATH
    )

    assert estimated_fee_without_account < estimated_fee

    # should not affect balance
    balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)
    assert balance == initial_balance

@pytest.mark.account
@devnet_in_background()
def test_low_max_fee():
    """Test if transaction is rejected with low max fee"""
    deploy_info = deploy_empty_contract()
    deploy_account_contract(salt=SALT)
    to_address = int(deploy_info["address"], 16)

    initial_balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)

    # get estimated fee for increase_balance call
    calls = [(to_address, "increase_balance", [10, 20])]
    estimated_fee = get_estimated_fee(calls, ACCOUNT_ADDRESS)

    max_fee = max(estimated_fee // 10, 1)
    tx_hash = execute(calls, ACCOUNT_ADDRESS, max_fee=max_fee)

    assert_tx_status(tx_hash, "REJECTED")

    balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)

    assert balance == initial_balance

@pytest.mark.account
@devnet_in_background()
def test_multicall():
    """Test making multiple calls."""
    deploy_info = deploy_empty_contract()
    deploy_account_contract(salt=SALT)
    to_address = int(deploy_info["address"], 16)

    # execute increase_balance calls
    calls = [
        (to_address, "increase_balance", [10, 20]),
        (to_address, "increase_balance", [30, 40])
    ]
    tx_hash = execute(calls, ACCOUNT_ADDRESS)

    assert_tx_status(tx_hash, "ACCEPTED_ON_L2")

    # check if nonce is increased
    nonce = get_nonce(ACCOUNT_ADDRESS)
    assert nonce == "1"

    # check if balance is increased
    balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)
    assert balance == "100"

def estimate_fee_local(req_dict: dict):
    """Estimate fee of a given transaction"""
    return requests.post(
        f"{GATEWAY_URL}/feeder_gateway/estimate_fee",
        json=req_dict
    )

@devnet_in_background()
def test_estimate_fee_in_unknown_address():
    """Call with unknown invoke function"""
    req_dict = json.loads(INVOKE_CONTENT)
    del req_dict["type"]
    resp = estimate_fee_local(req_dict)

    json_error_message = resp.json()["message"]
    msg = "Contract with address"
    assert resp.status_code == 500
    assert json_error_message.startswith(msg)

@devnet_in_background()
def test_estimate_fee_with_invalid_data():
    """Call estimate fee with invalid data on body"""
    req_dict = json.loads(DEPLOY_CONTENT)
    resp = estimate_fee_local(req_dict)

    json_error_message = resp.json()["message"]
    msg = "Invalid tx:"
    assert resp.status_code == 400
    assert msg in json_error_message
