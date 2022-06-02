"""Predeployed account tests"""

import pytest

from starkware.starknet.core.os.contract_hash import compute_contract_hash

from starknet_devnet.account import Account
from .util import assert_equal

@pytest.mark.account_predeployed
def test_precomputed_contract_hash():
    """Test if the precomputed hash of the account contract is correct."""
    recalculated_hash = compute_contract_hash(contract_definition=Account.get_definition())
    assert_equal(recalculated_hash, Account.HASH)
