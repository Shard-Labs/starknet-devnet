"""
File containing functions that wrap Starknet CLI commands.
"""

import atexit
import json
import os
import re
import subprocess
import sys
import time

from starkware.starknet.services.api.contract_definition import ContractDefinition

from starknet_devnet.general_config import DEFAULT_GENERAL_CONFIG
from .settings import GATEWAY_URL, FEEDER_GATEWAY_URL, HOST, PORT

class ReturnCodeAssertionError(AssertionError):
    """Error to be raised when the return code of an executed process is not as expected."""

def run_devnet_in_background(*args, sleep_seconds=5):
    """
    Runs starknet-devnet in background.
    By default sleeps 5 second after spawning devnet.
    Accepts extra args to pass to `starknet-devnet` command.
    Returns the process handle.
    """
    command = ["poetry", "run", "starknet-devnet", "--host", HOST, "--port", PORT, *args]
    # pylint: disable=consider-using-with
    proc = subprocess.Popen(command, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(sleep_seconds)
    atexit.register(proc.kill)
    return proc

def devnet_in_background(*devnet_args, **devnet_kwargs):
    """
    Decorator that runs devnet in background and later kills it.
    Prints devnet output in case of AssertionError.
    """
    def wrapper(func):
        def inner_wrapper(*args, **kwargs):
            proc = run_devnet_in_background(*devnet_args, **devnet_kwargs)
            try:
                func(*args, **kwargs)
            except AssertionError as error:
                proc.kill()
                stdout, stderr = proc.communicate()

                print("Devnet stdout:", file=sys.stderr)
                print(stdout.decode("utf-8"), file=sys.stderr)

                print("Devnet stderr:", file=sys.stderr)
                print(stderr.decode("utf-8"), file=sys.stderr)

                raise error
            finally:
                proc.kill()
        return inner_wrapper
    return wrapper

def assert_equal(actual, expected, explanation=None):
    """Assert that the two values are equal. Optionally provide explanation."""
    if actual != expected:
        if explanation:
            print("Assertion failed:", explanation)
        raise AssertionError(f"\nActual: {actual}\nExpected: {expected}")

def extract(regex, stdout):
    """Extract from `stdout` what matches `regex`."""
    matched = re.search(regex, stdout)
    if matched:
        return matched.group(1)
    raise RuntimeError(f"Cannot extract from {stdout}")

def extract_hash(stdout):
    """Extract tx_hash from stdout."""
    return extract(r"Transaction hash: (\w*)", stdout)

def extract_fee(stdout) -> int:
    """Extract fee from stdout."""
    return int(extract(r"(\d+)", stdout))

def extract_address(stdout):
    """Extract address from stdout."""
    return extract(r"Contract address: (\w*)", stdout)

def run_starknet(args, raise_on_nonzero=True, add_gateway_urls=True):
    """Wrapper around subprocess.run"""
    my_args = ["poetry", "run", "starknet", *args]
    if add_gateway_urls:
        my_args.extend([
            "--gateway_url", GATEWAY_URL,
            "--feeder_gateway_url", FEEDER_GATEWAY_URL
        ])
    output = subprocess.run(my_args, encoding="utf-8", check=False, capture_output=True)
    if output.returncode != 0 and raise_on_nonzero:
        if output.stderr:
            raise ReturnCodeAssertionError(output.stderr)
        raise ReturnCodeAssertionError(output.stdout)
    return output

def deploy(contract, inputs=None, salt=None):
    """Wrapper around starknet deploy"""
    args = ["deploy", "--contract", contract]
    if inputs:
        args.extend(["--inputs", *inputs])
    if salt:
        args.extend(["--salt", salt])
    output = run_starknet(args)
    return {
        "tx_hash": extract_hash(output.stdout),
        "address": extract_address(output.stdout)
    }

def assert_transaction(tx_hash, expected_status, expected_signature=None):
    """Wrapper around starknet get_transaction"""
    output = run_starknet(["get_transaction", "--hash", tx_hash])
    transaction = json.loads(output.stdout)
    assert_equal(transaction["status"], expected_status)
    if expected_signature:
        assert_equal(transaction["transaction"]["signature"], expected_signature)

def assert_transaction_not_received(tx_hash):
    """Assert correct tx response when there is no tx with `tx_hash`."""
    output = run_starknet(["get_transaction", "--hash", tx_hash])
    transaction = json.loads(output.stdout)
    assert_equal(transaction, {
        "status": "NOT_RECEIVED"
    })

def assert_transaction_receipt_not_received(tx_hash):
    """Assert correct tx receipt response when there is no tx with `tx_hash`."""
    output = run_starknet(["get_transaction_receipt", "--hash", tx_hash])
    receipt = json.loads(output.stdout)
    assert_equal(receipt, {
        "events": [],
        "l2_to_l1_messages": [],
        "status": "NOT_RECEIVED",
        "transaction_hash": tx_hash
    })

# pylint: disable=too-many-arguments
def invoke(function, inputs, address, abi_path, signature=None, max_fee=None):
    """Wrapper around starknet invoke. Returns tx hash."""
    args = [
        "invoke",
        "--function", function,
        "--inputs", *inputs,
        "--address", address,
        "--abi", abi_path,
    ]
    if signature:
        args.extend(["--signature", *signature])

    if max_fee:
        args.extend(["--max_fee", max_fee])

    output = run_starknet(args)

    print("Invoke successful!")
    return extract_hash(output.stdout)


def estimate_fee(function, inputs, address, abi_path, signature=None):
    """Wrapper around starknet estimate_fee. Returns fee in wei."""
    args = [
        "estimate_fee",
        "--function", function,
        "--inputs", *inputs,
        "--address", address,
        "--abi", abi_path,
    ]
    if signature:
        args.extend(["--signature", *signature])

    output = run_starknet(args)

    print("Estimate fee successful!")
    return extract_fee(output.stdout)


def call(function, address, abi_path, inputs=None):
    """Wrapper around starknet call"""
    args = [
        "call",
        "--function", function,
        "--address", address,
        "--abi", abi_path,
    ]
    if inputs:
        args.extend(["--inputs", *inputs])
    output = run_starknet(args)

    print("Call successful!")
    return output.stdout.rstrip()

def load_contract_definition(contract_path: str):
    """Loads the contract defintion from the contract path"""
    loaded_contract = load_json_from_path(contract_path)

    return ContractDefinition.load(loaded_contract)

def assert_tx_status(tx_hash, expected_tx_status):
    """Asserts the tx_status of the tx with tx_hash."""
    output = run_starknet(["tx_status", "--hash", tx_hash])
    tx_status = json.loads(output.stdout)["tx_status"]
    assert_equal(tx_status, expected_tx_status)

def assert_contract_code(address):
    """Asserts the content of the code of a contract at address."""
    output = run_starknet(["get_code", "--contract_address", address])
    code = json.loads(output.stdout)
    # just checking key equality
    assert_equal(sorted(code.keys()), ["abi", "bytecode"])

def assert_contract_definition(address, contract_path):
    """Asserts the content of the contract definition of a contract at address."""
    output = run_starknet(["get_full_contract", "--contract_address", address])
    contract_definition: ContractDefinition = ContractDefinition.load(json.loads(output.stdout))

    loaded_contract_definition = load_contract_definition(contract_path)

    assert_equal(contract_definition, loaded_contract_definition.remove_debug_info())

def assert_storage(address, key, expected_value):
    """Asserts the storage value stored at (address, key)."""
    output = run_starknet([
        "get_storage_at",
        "--contract_address", address,
        "--key", key
    ])
    assert_equal(output.stdout.rstrip(), expected_value)

def load_json_from_path(path):
    """Loads a json file from `path`."""
    with open(path, encoding="utf-8") as expected_file:
        return json.load(expected_file)

def assert_receipt(tx_hash, expected_path):
    """Asserts the content of the receipt of tx with tx_hash."""
    output = run_starknet(["get_transaction_receipt", "--hash", tx_hash])
    receipt = json.loads(output.stdout)
    expected_receipt = load_json_from_path(expected_path)

    assert_equal(receipt["transaction_hash"], tx_hash)

    for ignorable_key in ["block_hash", "transaction_hash"]:
        receipt.pop(ignorable_key)
        expected_receipt.pop(ignorable_key)
    assert_equal(receipt, expected_receipt)

def assert_events(tx_hash, expected_path):
    """Asserts the content of the events element of the receipt of tx with tx_hash."""
    output = run_starknet(["get_transaction_receipt", "--hash", tx_hash])
    receipt = json.loads(output.stdout)
    expected_receipt = load_json_from_path(expected_path)
    assert_equal(receipt["events"], expected_receipt["events"])

def get_block(block_number=None, parse=False):
    """Get the block with block_number. If no number provided, return the last."""
    args = ["get_block"]
    if block_number:
        args.extend(["--number", str(block_number)])
    if parse:
        output = run_starknet(args, raise_on_nonzero=True)
        return json.loads(output.stdout)

    return run_starknet(args, raise_on_nonzero=False)

def assert_negative_block_input():
    """Test behavior if get_block provided with negative input."""
    try:
        get_block(-1, parse=True)
        raise RuntimeError("Should have failed on negative block number")
    except ReturnCodeAssertionError:
        print("Correctly rejecting negative block number")

def assert_block(latest_block_number, latest_tx_hash):
    """Asserts the content of the block with block_number."""
    too_big = 1000
    error_message = get_block(block_number=too_big, parse=False).stderr
    total_blocks_str = re.search("There are currently (.*) blocks.", error_message).group(1)
    total_blocks = int(total_blocks_str)
    extracted_last_block_number = total_blocks - 1
    assert_equal(extracted_last_block_number, latest_block_number)

    latest_block = get_block(parse=True)
    specific_block = get_block(block_number=extracted_last_block_number, parse=True)
    assert_equal(latest_block, specific_block)

    assert_equal(latest_block["block_number"], latest_block_number)
    assert_equal(latest_block["status"], "ACCEPTED_ON_L2")

    latest_block_transactions = latest_block["transactions"]
    assert_equal(len(latest_block_transactions), 1)
    latest_transaction = latest_block_transactions[0]
    assert_equal(latest_transaction["transaction_hash"], latest_tx_hash)

    assert_equal(latest_block["sequencer_address"], hex(DEFAULT_GENERAL_CONFIG.sequencer_address))
    assert_equal(latest_block["gas_price"], hex(DEFAULT_GENERAL_CONFIG.min_gas_price))

def assert_block_hash(latest_block_number, expected_block_hash):
    """Asserts the content of the block with block_number."""

    block = get_block(block_number=latest_block_number, parse=True)
    assert_equal(block["block_hash"], expected_block_hash)
    assert_equal(block["status"], "ACCEPTED_ON_L2")

def assert_salty_deploy(contract_path, inputs, salt, expected_status, expected_address, expected_tx_hash):
    """Deploy with salt and assert."""

    deploy_info = deploy(contract_path, inputs, salt=salt)
    assert_tx_status(deploy_info["tx_hash"], expected_status)
    assert_equal(deploy_info["address"], expected_address)
    assert_equal(deploy_info["tx_hash"], expected_tx_hash)

def assert_failing_deploy(contract_path):
    """Run deployment for a contract that's expected to be rejected."""
    deploy_info = deploy(contract_path)
    assert_tx_status(deploy_info["tx_hash"], "REJECTED")

def load_file_content(file_name: str):
    """Load content of file located in the same directory as this test file."""
    full_file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(full_file_path, encoding="utf-8") as deploy_file:
        return deploy_file.read()
