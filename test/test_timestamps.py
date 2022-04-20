"""
Test block timestamps
"""

import pytest

from .shared import ARTIFACTS_PATH
from .util import devnet_in_background, deploy, call, get_block

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
    ))

def get_ts_from_last_block():
    """Returns the timestamp of the last block"""
    return get_block(parse=True)["timestamp"]

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
