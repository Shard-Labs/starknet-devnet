"""Fee token related tests."""

from test.settings import APP_URL
from test.test_account import deploy_empty_contract, execute, assert_tx_status, get_transaction_receipt, get_account_balance
import json
import pytest
import requests
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import calculate_contract_address_from_hash
from starknet_devnet.fee_token import FeeToken
from starknet_devnet.server import app
from .util import assert_equal, devnet_in_background, get_block

@pytest.mark.fee_token
def test_precomputed_contract_hash():
    """Assert that the precomputed hash in fee_token is correct."""
    recalculated_hash = compute_class_hash(FeeToken.get_contract_class())
    assert_equal(recalculated_hash, FeeToken.HASH)

@pytest.mark.fee_token
def test_precomputed_address():
    """Assert that the precomputed fee_token address is correct."""
    recalculated_address = calculate_contract_address_from_hash(
        salt=FeeToken.SALT,
        class_hash=FeeToken.HASH,
        constructor_calldata=FeeToken.CONSTRUCTOR_CALLDATA,
        deployer_address=0
    )
    assert_equal(recalculated_address, FeeToken.ADDRESS)

def mint(address: str, amount: int, lite=False):
    """Sends mint request; returns parsed json body"""
    response = requests.post(f"{APP_URL}/mint", json={
        "address": address,
        "amount": amount,
        "lite": lite
    })
    assert response.status_code == 200
    return response.json()

def mint_client(data: dict):
    """Send mint request to app test client"""
    return app.test_client().post(
        "/mint",
        content_type="application/json",
        data=json.dumps(data)
    )

def test_negative_mint():
    """Assert failure if mint amount negative"""
    resp = mint_client({
        "amount": -10,
        "address": "0x1"
    })

    assert resp.status_code == 400
    assert resp.json["message"] == "amount value must be greater than 0."

def test_mint_amount_not_int():
    """Assert failure if mint amount not int"""
    resp = mint_client({
        "amount": "abc",
        "address": "0x1"
    })

    assert resp.status_code == 400
    assert resp.json["message"] == "amount value must be an integer."

def test_missing_mint_amount():
    """Assert failure if mint amount missing"""
    resp = mint_client({
        "address": "0x1"
    })

    assert resp.status_code == 400
    assert resp.json["message"] == "amount value must be provided."

def test_wrong_mint_address_format():
    """Assert failure if mint address of wrong format"""
    resp = mint_client({
        "amount": 10,
        "address": "invalid_address"
    })

    assert resp.status_code == 400
    assert resp.json["message"] == "address value must be a hex string."

def test_missing_mint_address():
    """Assert failure if mint address missing"""
    resp = mint_client({
        "amount": 10
    })

    assert resp.status_code == 400
    assert resp.json["message"] == "address value must be provided."

@pytest.mark.fee_token
@devnet_in_background()
def test_mint():
    """Assert that mint will increase account balance and latest block created with correct transaction amount"""

    account_address = "0x6e3205f9b7c4328f00f718fdecf56ab31acfb3cd6ffeb999dcbac4123655502"
    response = mint(address=account_address, amount=50_000)
    assert response.get("new_balance") == 50_000
    assert response.get("unit") == "wei"
    assert response.get("tx_hash").startswith("0x")

    get_block(block_number="latest")
    response = requests.get(f"{APP_URL}/feeder_gateway/get_block?blockNumber=latest")
    assert response.status_code == 200
    assert response.json().get("block_number") == 0
    assert int(response.json().get("transactions")[0].get("calldata")[1], 16) == 50_000

@pytest.mark.fee_token
@devnet_in_background()
def test_mint_lite():
    """Assert that mint lite will increase account balance without producing block"""
    response = mint(
        address="0x34d09711b5c047471fd21d424afbf405c09fd584057e1d69c77223b535cf769",
        amount=50_000,
        lite=True
    )
    assert response.get("new_balance") == 50000
    assert response.get("unit") == "wei"
    assert response.get("tx_hash") is None

    response = requests.get(f"{APP_URL}/feeder_gateway/get_block?blockNumber=latest")
    assert response.status_code == 500
    assert response.json().get("message") == "Requested the latest block, but there are no blocks so far."

@pytest.mark.fee_token
@devnet_in_background(
    "--accounts", "1",
    "--seed", "42",
    "--gas-price", "100_000_000",
    "--initial-balance", "10"
)
def test_increase_balance():
    """Assert tx failure if insufficient funds; assert tx success after mint"""

    deploy_info = deploy_empty_contract()
    account_address = "0x347be35996a21f6bf0623e75dbce52baba918ad5ae8d83b6f416045ab22961a"
    private_key = 0xbdd640fb06671ad11c80317fa3b1799d
    to_address = int(deploy_info["address"], 16)
    initial_account_balance = get_account_balance(account_address)

    args = [10, 20]
    calls = [(to_address, "increase_balance", args)]
    invoke_tx_hash = execute(calls, account_address, private_key, max_fee=10 ** 21) # big enough

    assert_tx_status(invoke_tx_hash, "REJECTED")
    invoke_receipt = get_transaction_receipt(invoke_tx_hash)
    assert "subtraction overflow" in invoke_receipt["transaction_failure_reason"]["error_message"]

    intermediate_account_balance = get_account_balance(account_address)
    assert_equal(initial_account_balance, intermediate_account_balance)

    mint_amount = 200_000_000_000_000
    mint(address=account_address, amount=mint_amount)
    balance_after_mint = get_account_balance(account_address)
    assert_equal(balance_after_mint, initial_account_balance + mint_amount)

    invoke_tx_hash = execute(calls, account_address, private_key, max_fee=10 ** 21) # big enough
    assert_tx_status(invoke_tx_hash, "ACCEPTED_ON_L2")

    invoke_receipt = get_transaction_receipt(invoke_tx_hash)
    actual_fee = int(invoke_receipt["actual_fee"], 16)

    final_account_balance = get_account_balance(account_address)
    assert_equal(final_account_balance, initial_account_balance + mint_amount - actual_fee)
