"""
File containing functions that wrap Starknet CLI commands.
"""

import atexit
import json
import re
import subprocess
import time

from .settings import GATEWAY_URL, FEEDER_GATEWAY_URL, HOST, PORT

class ReturnCodeAssertionError(AssertionError):
    """Error to be raised when the return code of an executed process is not as expected."""

def run_devnet_in_background(sleep_seconds=0):
    """Run starknet-devnet in background. Return the process handle. Optionally sleep."""
    command = ["poetry", "run", "starknet-devnet", "--host", HOST, "--port", PORT]
    # pylint: disable=consider-using-with
    proc = subprocess.Popen(command, close_fds=True)
    time.sleep(sleep_seconds)
    atexit.register(proc.kill)

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

def extract_address(stdout):
    """Extract address from stdout."""
    return extract(r"Contract address: (\w*)", stdout)

def my_run(args, raise_on_nonzero=True, add_gateway_urls=True):
    """Wrapper around subprocess.run"""
    my_args = [*args]
    if add_gateway_urls:
        my_args.extend([
            "--gateway_url", GATEWAY_URL,
            "--feeder_gateway_url", FEEDER_GATEWAY_URL
        ])
    output = subprocess.run(my_args, encoding="utf-8", check=False, capture_output=True)
    if output.returncode != 0 and raise_on_nonzero:
        raise ReturnCodeAssertionError(output.stderr)
    return output

def deploy(contract, inputs=None, salt=None):
    """Wrapper around starknet deploy"""
    args = [
        "starknet", "deploy",
        "--contract", contract,
    ]
    if inputs:
        args.extend(["--inputs", *inputs])
    if salt:
        args.extend(["--salt", salt])
    output = my_run(args)
    return {
        "tx_hash": extract_hash(output.stdout),
        "address": extract_address(output.stdout)
    }

def assert_transaction(tx_hash, expected_status):
    """Wrapper around starknet get_transaction"""
    output = my_run([
        "starknet", "get_transaction",
        "--hash", tx_hash,
    ])
    transaction = json.loads(output.stdout)
    assert_equal(transaction["status"], expected_status)

def invoke(function, inputs, address, abi_path, signature=None):
    """Wrapper around starknet invoke"""
    args = [
        "starknet", "invoke",
        "--function", function,
        "--inputs", *inputs,
        "--address", address,
        "--abi", abi_path,
    ]
    if signature:
        args.extend(["--signature", *signature])
    output = my_run(args)

    print("Invoke successful!")
    return extract_hash(output.stdout)

def call(function, address, abi_path, inputs=None):
    """Wrapper around starknet call"""
    args = [
        "starknet", "call",
        "--function", function,
        "--address", address,
        "--abi", abi_path,
    ]
    if inputs:
        args.extend(["--inputs", *inputs])
    output = my_run(args)

    print("Call successful!")
    return output.stdout.rstrip()

def assert_tx_status(tx_hash, expected_tx_status):
    """Asserts the tx_status of the tx with tx_hash."""
    output = my_run([
        "starknet", "tx_status",
        "--hash", tx_hash
    ])
    tx_status = json.loads(output.stdout)["tx_status"]
    assert_equal(tx_status, expected_tx_status)

def assert_contract_code(address, expected_path):
    """Asserts the content of the code of a contract at address."""
    output = my_run([
        "starknet", "get_code",
        "--contract_address", address
    ])
    with open(expected_path, encoding="utf-8") as expected_file:
        assert_equal(output.stdout, expected_file.read())

def assert_storage(address, key, expected_value):
    """Asserts the storage value stored at (address, key)."""
    output = my_run([
        "starknet", "get_storage_at",
        "--contract_address", address,
        "--key", key
    ])
    assert_equal(output.stdout.rstrip(), expected_value)

EXPECTED_RECEIPT_PROPS = [
    "block_hash", "block_number", "execution_resources", "l2_to_l1_messages", "status", "transaction_hash", "transaction_index"
]
def assert_receipt(block_number, tx_hash):
    """Asserts the content of the receipt of tx with tx_hash."""
    output = my_run([
        "starknet", "get_transaction_receipt",
        "--hash", tx_hash
    ])
    receipt = json.loads(output.stdout)

    props_not_found = [prop for prop in EXPECTED_RECEIPT_PROPS if prop not in receipt]
    if props_not_found:
        raise RuntimeError(f"Receipt props not found:, {props_not_found}")

    assert_equal(receipt["block_number"], block_number)
    assert_equal(receipt["transaction_hash"], tx_hash)
    assert_equal(receipt["transaction_index"], 0)

def get_block(block_number=None, parse=False):
    """Get the block with block_number. If no number provided, return the last."""
    args = [
        "starknet", "get_block",
    ]
    if block_number:
        args.extend(["--number", str(block_number)])
    if parse:
        output = my_run(args, raise_on_nonzero=True)
        return json.loads(output.stdout)

    return my_run(args, raise_on_nonzero=False)

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
    assert_equal(latest_block["transactions"][0]["transaction_hash"], latest_tx_hash)

def assert_salty_deploy(contract_path, inputs, salt, expected_address, expected_tx_hash):
    """Run twice deployment with salt. Expect the same output."""
    for i in range(2):
        print(f"Running deployment {i})")
        deploy_info = deploy(contract_path, inputs, salt=salt)
        assert_tx_status(deploy_info["tx_hash"], "ACCEPTED_ON_L2")
        assert_equal(deploy_info["address"], expected_address)
        assert_equal(deploy_info["tx_hash"], expected_tx_hash)

def assert_failing_deploy(contract_path):
    """Run deployment for a contract that's expected to be rejected."""
    deploy_info = deploy(contract_path)
    assert_tx_status(deploy_info["tx_hash"], "REJECTED")
