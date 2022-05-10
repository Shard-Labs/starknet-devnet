"""
Test block timestamps
"""

import pytest
import requests

from .shared import ARTIFACTS_PATH
from .util import devnet_in_background, deploy, call, get_block
from .settings import APP_URL

TS_CONTRACT_PATH = f"{ARTIFACTS_PATH}/timestamp.cairo/timestamp.json"
TS_ABI_PATH = f"{ARTIFACTS_PATH}/timestamp.cairo/timestamp_abi.json"

SET_TIME_ARGUMENT = 1514764800

def deploy_ts_contract():
    """Deploys the timestamp contract"""
    return deploy(TS_CONTRACT_PATH)

def get_ts_from_contract(address):
    """Returns the timestamp of the contract"""
    return int(call(
        function="get_timestamp",
        address=address,
        abi_path=TS_ABI_PATH,
    ))

def get_ts_from_last_block():
    """Returns the timestamp of the last block"""
    return get_block(parse=True)["timestamp"]

def increase_time(time):
    """Increases the block timestamp offset"""
    return requests.post(f"{APP_URL}/increase_time", json={"time": time})

def set_time(time):
    """Sets the block timestamp offset"""
    return requests.post(f"{APP_URL}/set_time", json={"time": time})

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
    increase_time(86400)

    # deploy another contract contract to generate a new block
    deploy_ts_contract()

    second_block_ts = get_ts_from_last_block()

    assert second_block_ts - first_block_ts >= 86400

@pytest.mark.timestamps
@devnet_in_background()
def test_timestamps_set_time():
    """Test timestamp set time"""
    deploy_info = deploy_ts_contract()
    first_block_ts = get_ts_from_last_block()

    ts_from_first_call = get_ts_from_contract(deploy_info["address"])

    assert first_block_ts == ts_from_first_call

    # set time to 1 day after the deploy
    set_time(first_block_ts + 86400)

    ts_after_set = get_ts_from_last_block()

    assert ts_after_set == first_block_ts

    # generate a new block by deploying a new contract
    deploy_ts_contract()

    second_block_ts = get_ts_from_last_block()

    assert second_block_ts == first_block_ts + 86400

    # generate a new block by deploying a new contract
    deploy_ts_contract()

    third_block_ts = get_ts_from_last_block()

    # check if offset is still the same
    assert third_block_ts - first_block_ts >= 86400

@pytest.mark.timestamps
@devnet_in_background("--start-time", str(SET_TIME_ARGUMENT))
def test_timestamps_set_time_argument():
    """Test timestamp set time argument"""
    deploy_ts_contract()
    first_block_ts = get_ts_from_last_block()

    assert first_block_ts == SET_TIME_ARGUMENT

@pytest.mark.timestamps
@devnet_in_background()
def test_timestamps_set_time_errors():
    """Test timestamp set time negative"""
    deploy_ts_contract()

    response = set_time(-1)
    message = response.json()["message"]

    assert response.status_code == 400
    assert message == "Time value must be greater than 0."

    response = set_time(None)
    message = response.json()["message"]

    assert response.status_code == 400
    assert message == "Time value must be provided."

    response = set_time("not an int")
    message = response.json()["message"]

    assert response.status_code == 400
    assert message == "Time value must be an integer."

@pytest.mark.timestamps
@devnet_in_background()
def test_timestamps_increase_time_errors():
    """Test timestamp increase time negative"""
    deploy_ts_contract()

    response = increase_time(-1)
    message = response.json()["message"]

    assert response.status_code == 400
    assert message == "Time value must be greater than 0."

    response = increase_time(None)
    message = response.json()["message"]

    assert response.status_code == 400
    assert message == "Time value must be provided."

    response = increase_time("not an int")
    message = response.json()["message"]

    assert response.status_code == 400
    assert message == "Time value must be an integer."
