"""Fee token related tests."""

import pytest

from starkware.starknet.core.os.contract_hash import compute_contract_hash
from starkware.starknet.services.api.gateway.contract_address import (
    calculate_contract_address_from_hash,
)
from starknet_devnet.fee_token import FeeToken
from .util import assert_equal

@pytest.mark.fee_token
def test_precomputed_contract_hash():
    """Assert that the precomputed hash in fee_token is correct."""
    recalculated_hash = compute_contract_hash(FeeToken.get_definition())
    assert_equal(recalculated_hash, FeeToken.HASH)

@pytest.mark.fee_token
def test_precomputed_address():
    """Assert that the precomputed fee_token address is correct."""
    recalculated_address = calculate_contract_address_from_hash(
        salt=FeeToken.SALT,
        contract_hash=FeeToken.HASH,
        constructor_calldata=FeeToken.CONSTRUCTOR_CALLDATA,
        caller_address=0
    )
    assert_equal(recalculated_address, FeeToken.ADDRESS)
