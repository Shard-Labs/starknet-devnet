"""Predeployed account tests"""

import pytest

from starkware.starknet.core.os.class_hash import compute_class_hash

from starknet_devnet.account import Account
from .util import assert_equal

@pytest.mark.account_predeployed
def test_precomputed_contract_hash():
    """Test if the precomputed hash of the account contract is correct."""
    recalculated_hash = compute_class_hash(contract_class=Account.get_contract_class())
    assert_equal(recalculated_hash, Account.HASH)
