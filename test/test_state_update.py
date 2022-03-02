"""
Test get_state_update endpoint
"""

import pytest
import requests

from starkware.starknet.core.os.contract_hash import compute_contract_hash

from .util import deploy, invoke, load_contract_definition, run_devnet_in_background, get_block
from .settings import FEEDER_GATEWAY_URL

ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract.json"
ABI_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract_abi.json"
BALANCE_KEY = "916907772491729262376534102982219947830828984996257231353398618781993312401"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background()

    yield

    # after test
    devnet_proc.kill()

def get_state_update(block_hash = None):
    """Get state update"""
    res = requests.get(
        f"{FEEDER_GATEWAY_URL}/feeder_gateway/get_state_update",
        params={"blockHash":block_hash}
    )

    return res.json()

def deploy_empty_contract():
    """
    Deploy sample contract with balance = 0.
    Returns contract address.
    """
    deploy_dict = deploy(CONTRACT_PATH, inputs=["0"])
    contract_address = deploy_dict["address"]

    return contract_address

def get_contract_hash():
    """Get contract hash of the sample contract"""
    contract_definition = load_contract_definition(CONTRACT_PATH)

    return compute_contract_hash(contract_definition)

@pytest.mark.state_update
def test_initial_state_update():
    """Test initial state update"""
    state_update = get_state_update()

    assert state_update is None

@pytest.mark.state_update
def test_deployed_contracts():
    """Test deployed contracts in the state update"""
    contract_address = deploy_empty_contract()

    state_update = get_state_update()
    deployed_contracts = state_update.get("state_diff").get("deployed_contracts")

    assert len(deployed_contracts) == 1
    assert deployed_contracts[0].get("address") == contract_address

    deployed_contract_hash =  deployed_contracts[0].get("contract_hash")

    assert int(deployed_contract_hash, 16) == get_contract_hash()

@pytest.mark.state_update
def test_storage_diff():
    """Test storage diffs in the state update"""
    contract_address = deploy_empty_contract()
    invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH)

    state_update = get_state_update()

    storage_diffs = state_update.get("state_diff").get("storage_diffs")

    assert len(storage_diffs) == 1

    contract_storage_diffs = storage_diffs.get(contract_address)

    assert len(contract_storage_diffs) == 1
    assert contract_storage_diffs[0].get("value") == hex(30)
    assert contract_storage_diffs[0].get("key") == hex(int(BALANCE_KEY))

@pytest.mark.state_update
def test_block_hash():
    """Test block hash in the state update"""
    deploy_empty_contract()
    initial_state_update = get_state_update()

    first_block = get_block(parse=True)
    first_block_hash = first_block.get("block_hash")

    assert first_block_hash == initial_state_update.get("block_hash")

    # creates new block
    deploy_empty_contract()

    new_state_update = get_state_update()
    previous_state_update = get_state_update(first_block_hash)

    assert new_state_update["block_hash"] != first_block_hash
    assert previous_state_update == initial_state_update

@pytest.mark.state_update
def test_roots():
    """Test new root and old root in the state update"""
    deploy_empty_contract()
    state_update = get_state_update()

    new_root = state_update.get("new_root")

    assert new_root is not None
    assert state_update.get("old_root") is not None

    # creates new block
    deploy_empty_contract()

    state_update = get_state_update()
    old_root = state_update.get("old_root")

    assert old_root == new_root
