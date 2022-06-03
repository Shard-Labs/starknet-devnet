"""Fee token related tests."""

import pytest

from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.core.os.contract_address.contract_address import calculate_contract_address_from_hash
from starknet_devnet.fee_token import FeeToken
from .util import assert_equal

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
