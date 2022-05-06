"""
Test block timestamps
"""

import pytest
import requests

from .shared import ARTIFACTS_PATH
from .util import devnet_in_background, deploy, call, get_block, get_block
from .settings import APP_URL

TS_CONTRACT_PATH = f"{ARTIFACTS_PATH}/timestamp.cairo/timestamp.json"
TS_ABI_PATH = f"{ARTIFACTS_PATH}/timestamp.cairo/timestamp_abi.json"


def deploy_ts_contract():
    """Deploys the timestamp contract"""
    return deploy(TS_CONTRACT_PATH)

def get_ts_from_contract(address):
    """Returns the timestamp of the contract"""
    return int(call(
        function="get_timestamp",
        address=address,
        abi_path=TS_ABI_PATH,
    ), 16)

def get_ts_from_last_block():
    """Returns the timestamp of the last block"""
    return get_block(parse=True)["timestamp"]

def increase_time(time_ns):
    """Increases the block timestamp offset"""
    requests.post(f"{APP_URL}/increase_time", json={"time_ns": time_ns})

def set_time(time_ns):
    """Sets the block timestamp offset"""
    requests.post(f"{APP_URL}/set_time", json={"time_ns": time_ns})

@pytest.mark.timestamps
@devnet_in_background()
def test_timestamps():
    """Test timestamp"""
    deploy_info = deploy_ts_contract()
    ts_after_deploy = get_ts_from_last_block()

    ts_from_first_call = get_ts_from_contract(deploy_info["address"])

    assert ts_after_deploy == ts_from_first_call

    # deploy another contract contract to generate a new block
    deploy_ts_contract()
    ts_after_second_deploy = get_ts_from_last_block()

    assert ts_after_second_deploy > ts_from_first_call

    ts_from_second_call = get_ts_from_contract(deploy_info["address"])

    assert ts_after_second_deploy == ts_from_second_call
    assert ts_from_second_call > ts_from_first_call

@devnet_in_background()
def test_timestamps_increase_time():
    """Test timestamp increase time"""
    deploy_info = deploy_ts_contract()
    ts_after_deploy = get_ts_from_last_block()

    first_block_ts = get_ts_from_contract(deploy_info["address"])

    assert ts_after_deploy == first_block_ts

    # increase time by 1 day
    increase_time(86400000000000)

    # deploy another contract contract to generate a new block
    deploy_ts_contract()

    second_block_ts = get_ts_from_last_block()

    assert second_block_ts - first_block_ts >= 86400000000000

@pytest.mark.timestamps
@devnet_in_background()
def test_timestamps_set_time():
    """Test timestamp set time"""
    deploy_info = deploy_ts_contract()
    first_block_ts = get_ts_from_last_block()

    ts_from_first_call = get_ts_from_contract(deploy_info["address"])

    assert first_block_ts == ts_from_first_call

    # set time to 1 day after the deploy
    set_time(first_block_ts + 86400000000000)

    ts_after_set = get_ts_from_last_block()

    assert ts_after_set == first_block_ts

    # generate a new block by deploying a new contract
    deploy_ts_contract()

    second_block_ts = get_ts_from_last_block()

    assert second_block_ts == first_block_ts + 86400000000000

    # generate a new block by deploying a new contract
    deploy_ts_contract()

    third_block_ts = get_ts_from_last_block()

    # check if offset is still the same
    assert third_block_ts - first_block_ts >= 86400000000000
