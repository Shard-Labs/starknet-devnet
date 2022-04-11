"""
Test restart endpoint
"""

import pytest
import requests

from .settings import APP_URL, FEEDER_GATEWAY_URL
from .util import run_devnet_in_background, deploy, assert_transaction_not_received, assert_tx_status, call, invoke
from .shared import CONTRACT_PATH, ABI_PATH

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background()

    yield

    # after test
    devnet_proc.kill()

def restart():
    """Get restart response"""
    return requests.post(f"{APP_URL}/restart")

def get_state_update():
    """Get state update"""
    res = requests.get(f"{FEEDER_GATEWAY_URL}/feeder_gateway/get_state_update")
    return res.json()


def deploy_contract(salt=None):
    """Deploy empyt contract with balance of 0"""
    return deploy(CONTRACT_PATH, inputs=["0"], salt=salt)

@pytest.mark.restart
def test_restart_on_initial_state():
    """Checks restart endpoint when there were no changes"""
    res = restart()
    assert res.status_code == 200


@pytest.mark.restart
def test_transaction():
    """Checks that there is no deploy transaction after the restart"""
    deploy_info = deploy_contract()
    tx_hash = deploy_info["tx_hash"]
    assert_tx_status(tx_hash, "ACCEPTED_ON_L2")

    restart()

    assert_transaction_not_received(tx_hash=tx_hash)

@pytest.mark.restart
def test_contract():
    """Checks if contract storage is reset"""
    salt = "0x99"
    deploy_info = deploy_contract(salt)
    contract_address =  deploy_info["address"]
    balance = call("get_balance", contract_address, ABI_PATH)
    assert balance == "0"

    invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH)
    balance = call("get_balance", contract_address, ABI_PATH)

    assert balance == "30"

    restart()

    deploy_contract(salt)
    balance = call("get_balance", contract_address, ABI_PATH)
    assert balance == "0"

@pytest.mark.restart
def test_state_update():
    """Checks if state update is reset"""
    deploy_contract()
    state_update = get_state_update()

    assert state_update is not None

    restart()

    state_update = get_state_update()

    assert state_update is None
