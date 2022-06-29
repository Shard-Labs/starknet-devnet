"""Fee token related tests."""
from test.settings import GATEWAY_URL
import pytest
import requests
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import calculate_contract_address_from_hash
from starknet_devnet.fee_token import FeeToken
from .util import assert_equal, devnet_in_background

ACCOUNTS_SEED_DEVNET_ARGS = [
    "--accounts",
    "3",
    "--seed",
    "123",
     "--initial-balance",
    "10_000",
]

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
@devnet_in_background(*ACCOUNTS_SEED_DEVNET_ARGS)
def test_mint():
    """Asert that mint will increase account balance"""
    json_load = {
        "address": "0x6e3205f9b7c4328f00f718fdecf56ab31acfb3cd6ffeb999dcbac41236ea502",
        "amount": 50_000
    }
    response = requests.post(f"{GATEWAY_URL}/mint", json=json_load)
    assert response.status_code == 200
    assert response.json().get('new_balance') == 60000

@pytest.mark.fee_token
@devnet_in_background(*ACCOUNTS_SEED_DEVNET_ARGS)
def test_mint_lite():
    """Asert that mint lite will increase account balance"""
    json_load = {
        "address": "0x6e3205f9b7c4328f00f718fdecf56ab31acfb3cd6ffeb999dcbac41236ea502",
        "amount": 50_000,
        "lite": True
    }
    response = requests.post(f"{GATEWAY_URL}/mint", json=json_load)
    assert response.status_code == 200
    assert response.json().get('new_balance') == 60000
