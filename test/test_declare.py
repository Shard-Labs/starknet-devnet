"""
Tests of contract class declaration and deploy syscall.
"""

import pytest

from .shared import (
    ABI_PATH,
    CONTRACT_PATH,
    DEPLOYER_ABI_PATH,
    DEPLOYER_CONTRACT_PATH,
    EXPECTED_CLASS_HASH
)
from .util import (
    assert_contract_class,
    assert_equal,
    assert_hex_equal,
    assert_tx_status,
    call,
    declare,
    deploy,
    devnet_in_background,
    get_class_by_hash,
    get_class_hash_at,
    get_transaction_receipt,
    invoke
)

@pytest.mark.declare
@devnet_in_background("--accounts", "0")
def test_declare_and_deploy():
    """
    Test declaring a class and deploying it through an account.
    """

    # Declare the class to be deployed
    declare_info = declare(contract=CONTRACT_PATH)
    class_hash = declare_info["class_hash"]
    assert_hex_equal(class_hash, EXPECTED_CLASS_HASH)

    contract_class = get_class_by_hash(class_hash=class_hash)
    assert_contract_class(contract_class, CONTRACT_PATH)

    # Deploy the deployer
    deployer_deploy_info = deploy(
        contract=DEPLOYER_CONTRACT_PATH,
        inputs=[declare_info["class_hash"]]
    )
    deployer_address = deployer_deploy_info["address"]

    # Deploy a contract of the declared class through the deployer
    initial_balance = "10"
    invoke_tx_hash = invoke(
        function="deploy_contract",
        inputs=[initial_balance],
        address=deployer_address,
        abi_path=DEPLOYER_ABI_PATH
    )
    assert_tx_status(invoke_tx_hash, "ACCEPTED_ON_L2")

    # Get deployment address from emitted event
    tx_receipt = get_transaction_receipt(tx_hash=invoke_tx_hash)
    events = tx_receipt["events"]
    assert_equal(len(events), 1, explanation=events)
    event = events[0]
    assert_equal(len(event["data"]), 1, explanation=events)
    contract_address = event["data"][0]

    # Test deployed contract
    fetched_class_hash = get_class_hash_at(contract_address=contract_address)
    assert_hex_equal(fetched_class_hash, EXPECTED_CLASS_HASH)

    balance = call(
        function="get_balance",
        address=contract_address,
        abi_path=ABI_PATH
    )
    assert_equal(balance, initial_balance)
