"""Fee token related tests."""
from test.settings import GATEWAY_URL
from test.test_account import deploy_empty_contract, execute, assert_tx_status, get_transaction_receipt, get_account_balance, call, ABI_PATH
import pytest
import requests
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import calculate_contract_address_from_hash
from starknet_devnet.fee_token import FeeToken
from .util import assert_equal, devnet_in_background

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

@pytest.mark.fee_token
@devnet_in_background()
def test_mint():
    """Assert that mint will increase account balance and latest block created with correct transaction amount"""

    json_load = {
        "address": "0x6e3205f9b7c4328f00f718fdecf56ab31acfb3cd6ffeb999dcbac4123655502",
        "amount": 50_000
    }
    response = requests.post(f"{GATEWAY_URL}/mint", json=json_load)
    assert response.status_code == 200
    assert response.json().get('new_balance') == 50_000

    response = requests.get(f"{GATEWAY_URL}/feeder_gateway/get_block?blockNumber=latest")
    assert response.status_code == 200
    assert response.json().get('block_number') == 0
    assert int(response.json().get('transactions')[0].get('calldata')[1], 16) == 50_000

@pytest.mark.fee_token
@devnet_in_background()
def test_mint_lite():
    """Assert that mint lite will increase account balance without producing block"""
    json_load = {
        "address": "0x34d09711b5c047471fd21d424afbf405c09fd584057e1d69c77223b535cf769",
        "amount": 50_000,
        "lite": True
    }
    response = requests.post(f"{GATEWAY_URL}/mint", json=json_load)
    assert response.status_code == 200
    assert response.json().get('new_balance') == 50000

    response = requests.get(f"{GATEWAY_URL}/feeder_gateway/get_block?blockNumber=latest")
    assert response.status_code == 500
    assert response.json().get('message') == 'Requested the latest block, but there are no blocks so far.'

@pytest.mark.fee_token
@devnet_in_background(
    "--accounts", "1",
    "--seed", "42",
    "--gas-price", "100_000_000",
    "--initial-balance", "10"
)
def test_increase_balance():
    '''Assert no funds for transaction than mint funds and success transaction'''
    deploy_info = deploy_empty_contract()
    account_address = "0x347be35996a21f6bf0623e75dbce52baba918ad5ae8d83b6f416045ab22961a"
    private_key = 0xbdd640fb06671ad11c80317fa3b1799d
    to_address = int(deploy_info["address"], 16)
    initial_account_balance = get_account_balance(account_address)
    initial_contract_balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)

    args = [10, 20]
    calls = [(to_address, "increase_balance", args)]
    invoke_tx_hash = execute(calls, account_address, private_key, max_fee=10 ** 21) # big enough

    assert_tx_status(invoke_tx_hash, "REJECTED")
    invoke_receipt = get_transaction_receipt(invoke_tx_hash)
    assert "subtraction overflow" in invoke_receipt["transaction_failure_reason"]["error_message"]

    final_contract_balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)
    assert_equal(final_contract_balance, initial_contract_balance)

    final_account_balance = get_account_balance(account_address)
    assert_equal(initial_account_balance, final_account_balance)

    json_load = {
        "address": "0x347be35996a21f6bf0623e75dbce52baba918ad5ae8d83b6f416045ab22961a",
        "amount": 200_000_000_000_000
    }
    response = requests.post(f"{GATEWAY_URL}/mint", json=json_load)
    assert response.status_code == 200
    invoke_tx_hash = execute(calls, account_address, private_key, max_fee=10 ** 21) # big enough
    assert_tx_status(invoke_tx_hash, "ACCEPTED_ON_L2")
    final_account_balance = get_account_balance(account_address)
    assert initial_account_balance != final_account_balance
