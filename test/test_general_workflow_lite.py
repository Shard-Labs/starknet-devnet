"""
Lite run of the main test script. Tests that main functionalities don't have issues when running lite mode
"""

import pytest

from .util import (
    assert_block_hash,
    assert_negative_block_input,
    run_devnet_in_background,
    assert_equal,
    assert_tx_status,
    call, deploy, invoke
)

from .shared import (
    ABI_PATH,
    CONTRACT_PATH
)

NONEXISTENT_TX_HASH = "0x12345678910111213"
BALANCE_KEY = "916907772491729262376534102982219947830828984996257231353398618781993312401"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background("--lite-mode")

    yield

    # after test
    devnet_proc.kill()

@pytest.mark.test_general_workflow
def test_general_workflow_lite():
    """Test devnet with CLI"""
    deploy_info = deploy(CONTRACT_PATH, ["0"])

    print("Deployment:", deploy_info)

    assert_tx_status(deploy_info["tx_hash"], "ACCEPTED_ON_L2")
    assert_equal(deploy_info["tx_hash"],"0x0")

    # check block and receipt after deployment
    assert_negative_block_input()
    assert_block_hash(0, "0x0")

    # increase and assert balance
    invoke(
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

    assert_block_hash(1, "0x1")
