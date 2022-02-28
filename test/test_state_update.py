"""
Test get_state_update endpoint
"""

import pytest
import requests

from .util import deploy, invoke, run_devnet_in_background
from .settings import FEEDER_GATEWAY_URL

ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract.json"
ABI_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract_abi.json"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background()
    # devnet_proc.wait()

    yield

    # after test
    devnet_proc.kill()


def get_state_update():
    """Get state update"""
    res =  requests.get(f"{FEEDER_GATEWAY_URL}/feeder_gateway/get_state_update")

    return res.json()



def deploy_empty_contract():
    """
    Deploy sample contract with balance = 0.
    Returns contract address.
    """
    deploy_dict = deploy(CONTRACT_PATH, inputs=["0"])
    contract_address = deploy_dict["address"]

    return contract_address


@pytest.mark.state_update
def test_initial_state_update():
    """Test initial state update"""
    state_update = get_state_update()

    assert state_update is None

@pytest.mark.state_update
def test_deployed_contracts():
    """Test deployed contracts in the state update"""
    contract_address = deploy_empty_contract()
    invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH)

    state_update = get_state_update()

    # this should fail
    assert state_update is None

@pytest.mark.state_update
def test_storage_diff():
    """Test storage diffs in the state update"""
    pass

@pytest.mark.state_update
def test_roots():
    """Test new root and old root in the state update"""
    pass
