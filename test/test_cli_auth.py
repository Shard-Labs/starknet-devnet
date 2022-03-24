"""
Tests how signed interaction with a Starknet contract.
"""
import pytest

from .util import (
    run_devnet_in_background,
    assert_block, assert_equal, assert_receipt,
    assert_storage, assert_transaction, assert_tx_status,
    call, deploy, invoke
)

from .shared import ARTIFACTS_PATH, SIGNATURE

CONTRACT_PATH = f"{ARTIFACTS_PATH}/auth_contract.cairo/auth_contract.json"
ABI_PATH = f"{ARTIFACTS_PATH}/auth_contract.cairo/auth_contract_abi.json"

# PRIVATE_KEY = "12345"
PUBLIC_KEY = "1628448741648245036800002906075225705100596136133912895015035902954123957052"
INITIAL_BALANCE = "1000"

SIGNATURE = [
        "1225578735933442828068102633747590437426782890965066746429241472187377583468",
        "3568809569741913715045370357918125425757114920266578211811626257903121825123"
]
BALANCE_KEY = "142452623821144136554572927896792266630776240502820879601186867231282346767"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background(sleep_seconds=20)

    yield

    # after test
    devnet_proc.kill()

@pytest.mark.cli
def test_starknet_cli_auth():
    """Test CLI auth in devnet"""

    deploy_info = deploy(CONTRACT_PATH, [PUBLIC_KEY, INITIAL_BALANCE])
    print("Deployment:", deploy_info)

    assert_tx_status(deploy_info["tx_hash"], "ACCEPTED_ON_L2")
    assert_transaction(deploy_info["tx_hash"], "ACCEPTED_ON_L2")

    # check block and receipt after deployment
    assert_block(0, deploy_info["tx_hash"])
    assert_receipt(deploy_info["tx_hash"], "test/expected/deploy_receipt_auth.json")


    # increase and assert balance
    invoke_tx_hash = invoke(
        function="increase_balance",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=[PUBLIC_KEY, "4321"],
        signature=SIGNATURE
    )
    value = call(
        function="get_balance",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=[PUBLIC_KEY]
    )
    assert_equal(value, "5321", "Invoke+call failed!")

    # check storage after deployment
    assert_storage(deploy_info["address"], BALANCE_KEY, "0x14c9")
    assert_transaction(invoke_tx_hash, "ACCEPTED_ON_L2", expected_signature=SIGNATURE)
    assert_receipt(invoke_tx_hash, "test/expected/invoke_receipt_auth.json")
