"""Fee estimation tests"""

import json

import pytest
import requests

from .util import (
    deploy,
    devnet_in_background,
    load_file_content
)
from .settings import APP_URL
from .shared import CONTRACT_PATH

DEPLOY_CONTENT = load_file_content("deploy.json")
INVOKE_CONTENT = load_file_content("invoke.json")

def estimate_fee_local(req_dict: dict):
    """Estimate fee of a given transaction"""
    return requests.post(
        f"{APP_URL}/feeder_gateway/estimate_fee",
        json=req_dict
    )

def send_estimate_fee_with_requests(req_dict: dict):
    """Sends the estimate fee dict in a POST request and returns the response data."""
    return requests.post(
        f"{APP_URL}/feeder_gateway/estimate_fee",
        json=req_dict
    )

@devnet_in_background()
def test_estimate_fee_without_block_zero_gas():
    """Call without transaction, expect pass with gas_price zero"""
    response = send_estimate_fee_with_requests({
        "entry_point_selector": "0x2f0b3c5710379609eb5495f1ecd348cb28167711b73609fe565a72734550354",
        "calldata": [
            "1786654640273905855542517570545751199272449814774211541121677632577420730552",
            "1000000000000000000000",
            "0"
        ],
        "signature": [],
        "contract_address": "0x62230ea046a9a5fbc261ac77d03c8d41e5d442db2284587570ab46455fd2488"
    })

    assert response.status_code == 200
    response_parsed = response.json()
    assert response_parsed["gas_price"] == 0
    assert response_parsed["gas_usage"] == 0
    assert response_parsed["overall_fee"] == 0
    assert response_parsed["unit"] == "wei"
    assert response_parsed["warning"] == "block isn't produced"

@pytest.mark.estimate_fee
@devnet_in_background()
def test_estimate_fee_in_unknown_address():
    """Call with unknown invoke function"""
    req_dict = json.loads(INVOKE_CONTENT)
    del req_dict["type"]
    resp = estimate_fee_local(req_dict)

    json_error_message = resp.json()["message"]
    assert resp.status_code == 500
    assert json_error_message.startswith("Contract with address")

@pytest.mark.estimate_fee
@devnet_in_background()
def test_estimate_fee_with_invalid_data():
    """Call estimate fee with invalid data on body"""
    req_dict = json.loads(DEPLOY_CONTENT)
    resp = estimate_fee_local(req_dict)

    json_error_message = resp.json()["message"]
    assert resp.status_code == 400
    assert "Invalid Starknet function call" in json_error_message

GAS_PRICE = int(1e11)

@pytest.mark.estimate_fee
@devnet_in_background("--gas-price", str(GAS_PRICE))
def test_estimate_fee_with_complete_request_data():
    """Estimate fee with complete request data"""

    deploy_info = deploy(CONTRACT_PATH, ["0"])
    # increase balance with 10+20
    response = send_estimate_fee_with_requests({
        "contract_address": deploy_info["address"],
        "version": "0x100000000000000000000000000000000",
        "signature": [],
        "calldata": ["10", "20"],
        "max_fee": "0x0",
        "entry_point_selector": "0x362398bec32bc0ebb411203221a35a0301193a96f317ebe5e40be9f60d15320"
    })

    assert response.status_code == 200
    response_parsed = response.json()

    assert response_parsed["gas_price"] == GAS_PRICE
    assert isinstance(response_parsed["gas_usage"], int)
    assert response_parsed["overall_fee"] == response_parsed["gas_price"] * response_parsed["gas_usage"]
    assert response_parsed["unit"] == "wei"
