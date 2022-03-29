"""
Tests the general workflow of the devnet.
"""

import pytest

from .util import (
    assert_contract_definition,
    assert_negative_block_input,
    assert_transaction_not_received,
    assert_transaction_receipt_not_received,
    run_devnet_in_background,
    assert_block, assert_contract_code, assert_equal, assert_failing_deploy, assert_receipt, assert_salty_deploy,
    assert_storage, assert_transaction, assert_tx_status, assert_events,
    call, deploy, invoke
)

from .shared import (
    ABI_PATH,
    BALANCE_KEY,
    CONTRACT_PATH,
    EVENTS_ABI_PATH,
    EVENTS_CONTRACT_PATH,
    EXPECTED_SALTY_DEPLOY_ADDRESS,
    EXPECTED_SALTY_DEPLOY_HASH,
    FAILING_CONTRACT_PATH,
    NONEXISTENT_TX_HASH
)

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background()

    yield

    # after test
    devnet_proc.kill()

@pytest.mark.general_workflow
def test_general_workflow():
    """Test devnet with CLI"""
    deploy_info = deploy(CONTRACT_PATH, ["0"])

    print("Deployment:", deploy_info)

    assert_tx_status(deploy_info["tx_hash"], "ACCEPTED_ON_L2")
    assert_transaction(deploy_info["tx_hash"], "ACCEPTED_ON_L2")
    assert_transaction_not_received(NONEXISTENT_TX_HASH)

    # check storage after deployment
    assert_storage(deploy_info["address"], BALANCE_KEY, "0x0")

    # check block and receipt after deployment
    assert_negative_block_input()

    assert_block(0, deploy_info["tx_hash"])
    assert_receipt(deploy_info["tx_hash"], "test/expected/deploy_receipt.json")
    assert_transaction_receipt_not_received(NONEXISTENT_TX_HASH)

    # check code
    assert_contract_code(deploy_info["address"])

    # check contract definition
    assert_contract_definition(deploy_info["address"], CONTRACT_PATH)

    # increase and assert balance
    invoke_tx_hash = invoke(
        function="increase_balance",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["10", "20"]
    )
    value = call(
        function="get_balance",
        address=deploy_info["address"],
        abi_path=ABI_PATH
    )
    assert_equal(value, "30", "Invoke+call failed!")

    # check storage, block and receipt after increase
    assert_storage(deploy_info["address"], BALANCE_KEY, "0x1e")
    assert_block(1, invoke_tx_hash)
    assert_receipt(invoke_tx_hash, "test/expected/invoke_receipt.json")

    # check handling complex input
    value = call(
        function="sum_point_array",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["2", "10", "20", "30", "40"]
    )
    assert_equal(value, "40 60", "Checking complex input failed!")

    # check deploy when a salt is provided, and use the same contract to test events
    assert_salty_deploy(
        contract_path=EVENTS_CONTRACT_PATH,
        salt="0x99",
        inputs=None,
        expected_address=EXPECTED_SALTY_DEPLOY_ADDRESS,
        expected_tx_hash=EXPECTED_SALTY_DEPLOY_HASH
    )

    salty_invoke_tx_hash = invoke(
        function="increase_balance",
        address=EXPECTED_SALTY_DEPLOY_ADDRESS,
        abi_path=EVENTS_ABI_PATH,
        inputs=["10"]
    )

    assert_events(salty_invoke_tx_hash, "test/expected/invoke_receipt_event.json")

    assert_failing_deploy(contract_path=FAILING_CONTRACT_PATH)
