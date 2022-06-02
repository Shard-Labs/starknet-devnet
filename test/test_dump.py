"""
Test server state serialization (dumping/loading).
"""

from asyncio import subprocess
import os
import signal
import time
import requests

import pytest

from .util import call, deploy, devnet_in_background, invoke, run_devnet_in_background, terminate_and_wait
from .settings import GATEWAY_URL
from .shared import CONTRACT_PATH, ABI_PATH

DUMP_PATH = "dump.pkl"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Cleanup after tests finish."""

    # before test
    # nothing

    yield

    # after test
    for path in os.listdir():
        if path.endswith(".pkl"):
            os.remove(path)

def send_dump_request(dump_path: str=None):
    """Send HTTP request to trigger dumping."""
    json_load = { "path": dump_path } if dump_path else None
    return requests.post(f"{GATEWAY_URL}/dump", json=json_load)

def send_error_request():
    """Send HTTP request to trigger error response."""
    json_body = { "dummy": "dummy_value" }
    return requests.post(f"{GATEWAY_URL}/dump", json=json_body)

def assert_dump_present(dump_path: str, sleep_seconds=2):
    """Assert there is a non-empty dump file."""
    time.sleep(sleep_seconds)
    assert os.path.isfile(dump_path)
    assert os.path.getsize(dump_path) > 0

def assert_no_dump_present(dump_path: str, sleep_seconds=2):
    """Assert there is no dump file."""
    time.sleep(sleep_seconds)
    assert not os.path.isfile(dump_path)

def dump_and_assert(dump_path: str=None):
    """Assert no dump file before dump and assert some dump file after dump."""
    assert_no_dump_present(dump_path)
    resp = send_dump_request(dump_path)
    assert resp.status_code == 200
    assert_dump_present(dump_path)

def assert_not_alive():
    """Assert devnet is not alive."""
    try:
        requests.get(f"{GATEWAY_URL}/is_alive")
        raise RuntimeError("Should have failed before this line.")
    except requests.exceptions.ConnectionError:
        pass

def deploy_empty_contract():
    """
    Deploy sample contract with balance = 0.
    Returns contract address.
    """
    deploy_dict = deploy(CONTRACT_PATH, inputs=["0"])
    contract_address = deploy_dict["address"]
    initial_balance = call("get_balance", contract_address, ABI_PATH)
    assert initial_balance == "0"
    return contract_address

def test_load_if_no_file():
    """Test loading if dump file not present."""
    assert_no_dump_present(DUMP_PATH)
    devnet_proc = run_devnet_in_background("--load-path", DUMP_PATH, stderr=subprocess.PIPE)
    devnet_proc.wait()
    try:
        assert devnet_proc.returncode != 0
        expected_msg = f"Error: Cannot load from {DUMP_PATH}. Make sure the file exists and contains a Devnet dump."
        assert expected_msg in devnet_proc.stderr.read().decode("utf-8")
    finally:
        terminate_and_wait(devnet_proc)

def test_dumping_if_path_not_provided():
    """Assert failure if dumping attempted without a known path."""
    devnet_proc = run_devnet_in_background()
    try:
        resp = send_dump_request()
        assert resp.status_code == 400
    finally:
        terminate_and_wait(devnet_proc)

def test_dumping_if_path_provided_as_cli_option():
    """Test dumping if path provided as CLI option"""
    devnet_proc = run_devnet_in_background("--dump-path", DUMP_PATH)
    try:
        resp = send_dump_request()
        assert resp.status_code == 200
        assert_dump_present(DUMP_PATH)
    finally:
        terminate_and_wait(devnet_proc)

def test_dumping_via_endpoint():
    """Test dumping via endpoint."""
    # init devnet + contract
    devnet_proc = run_devnet_in_background()
    contract_address = deploy_empty_contract()

    invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH)
    balance_after_invoke = call("get_balance", contract_address, ABI_PATH)
    assert balance_after_invoke == "30"

    dump_and_assert(DUMP_PATH)

    terminate_and_wait(devnet_proc)
    assert_not_alive()

    # spawn new devnet, load from dump path
    loaded_devnet_proc = run_devnet_in_background("--load-path", DUMP_PATH)
    loaded_balance = call("get_balance", contract_address, ABI_PATH)
    assert loaded_balance == balance_after_invoke

    # assure that new invokes can be made
    invoke("increase_balance", ["15", "25"], contract_address, ABI_PATH)
    balance_after_invoke_on_loaded = call("get_balance", contract_address, abi_path=ABI_PATH)
    assert balance_after_invoke_on_loaded == "70"

    os.remove(DUMP_PATH)
    terminate_and_wait(loaded_devnet_proc)
    assert_no_dump_present(DUMP_PATH)

def test_dumping_on_exit():
    """Test dumping on exit."""
    devnet_proc = run_devnet_in_background("--dump-on", "exit", "--dump-path", DUMP_PATH,sleep_seconds=3)
    try:
        contract_address = deploy_empty_contract()

        invoke("increase_balance", ["10", "20"], contract_address, ABI_PATH)
        balance_after_invoke = call("get_balance", contract_address, ABI_PATH)
        assert balance_after_invoke == "30"

        assert_no_dump_present(DUMP_PATH)
        devnet_proc.send_signal(signal.SIGINT) # simulate Ctrl+C because devnet can't handle kill
        assert_dump_present(DUMP_PATH, sleep_seconds=3)
    finally:
        terminate_and_wait(devnet_proc)

def test_invalid_dump_on_option():
    """Test behavior when invalid dump-on is provided."""
    devnet_proc = run_devnet_in_background(
        "--dump-on", "obviously-invalid",
        "--dump-path", DUMP_PATH,
        stderr=subprocess.PIPE
    )
    devnet_proc.wait()

    try:
        assert devnet_proc.returncode != 0
        expected_msg = b"Error: Invalid --dump-on option: obviously-invalid. Valid options: exit, transaction\n"
        assert devnet_proc.stderr.read() == expected_msg
    finally:
        terminate_and_wait(devnet_proc)

def test_dump_path_not_present_with_dump_on_present():
    """Test behavior when dump-path is not present and dump-on is."""
    devnet_proc = run_devnet_in_background("--dump-on", "exit", stderr=subprocess.PIPE)
    devnet_proc.wait()

    try:
        assert devnet_proc.returncode != 0
        expected_msg = b"Error: --dump-path required if --dump-on present\n"
        assert devnet_proc.stderr.read() == expected_msg
    finally:
        terminate_and_wait(devnet_proc)

def assert_load(dump_path: str, contract_address: str, expected_value: str):
    """Load from `dump_path` and assert get_balance at `contract_address` returns `expected_value`."""
    devnet_loaded_proc = run_devnet_in_background("--load-path", dump_path)
    try:
        assert call("get_balance", contract_address, ABI_PATH) == expected_value
    finally:
        terminate_and_wait(devnet_loaded_proc)
        os.remove(dump_path)

def test_dumping_on_each_tx():
    """Test dumping on each transaction."""
    devnet_proc = run_devnet_in_background("--dump-on", "transaction", "--dump-path", DUMP_PATH)

    try:
        # deploy
        contract_address = deploy_empty_contract()
        assert_dump_present(DUMP_PATH)
        dump_after_deploy_path = "dump_after_deploy.pkl"
        os.rename(DUMP_PATH, dump_after_deploy_path)

        # invoke
        invoke("increase_balance", ["5", "5"], contract_address, ABI_PATH)
        assert_dump_present(DUMP_PATH)
        dump_after_invoke_path = "dump_after_invoke.pkl"
        os.rename(DUMP_PATH, dump_after_invoke_path)

        terminate_and_wait(devnet_proc)

        assert_load(dump_after_deploy_path, contract_address, "0")
        assert_load(dump_after_invoke_path, contract_address, "10")
    finally:
        terminate_and_wait(devnet_proc)

@devnet_in_background()
def test_dumping_call_with_invalid_body():
    """Call with invalid body and test status code and message."""
    resp = send_error_request()

    json_error_message = resp.json()["message"]
    msg = "No path provided."
    assert msg == json_error_message
    assert resp.status_code == 400
