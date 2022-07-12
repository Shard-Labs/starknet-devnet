"""Predeployed account tests"""

import pytest
import requests

from starkware.starknet.core.os.class_hash import compute_class_hash
from starknet_devnet.account import Account
from .util import assert_equal, devnet_in_background
from .support.assertions import assert_valid_schema
from .settings import APP_URL

ACCOUNTS_SEED_DEVNET_ARGS = [
    "--accounts",
    "3",
    "--seed",
    "123",
    "--gas-price",
    "100",
    "--initial-balance",
    "1_000",
]


@pytest.mark.account_predeployed
def test_precomputed_contract_hash():
    """Test if the precomputed hash of the account contract is correct."""
    recalculated_hash = compute_class_hash(contract_class=Account.get_contract_class())
    assert_equal(recalculated_hash, Account.HASH)


@pytest.mark.account_predeployed
@devnet_in_background(*ACCOUNTS_SEED_DEVNET_ARGS)
def test_predeployed_accounts_predefined_values():
    """Test if --account --seed --initial-balance return exact calculated values"""
    response = requests.get(f"{APP_URL}/predeployed_accounts")
    assert response.status_code == 200
    assert_valid_schema(response.json(), "predeployed_accounts_fixed_seed.json")
