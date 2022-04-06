"""
Test account functionality.
"""

import pytest

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.signature import private_to_stark_key, sign
from starkware.starknet.public.abi import get_selector_from_name

from .shared import ABI_PATH, CONTRACT_PATH
from .util import assert_tx_status, deploy, run_devnet_in_background, call, invoke

ACCOUNT_ARTIFACTS_PATH = "starknet_devnet/accounts_artifacts"
ACCOUNT_AUTHOR = "OpenZeppelin"
ACCOUNT_VERSION = "0.1.0"

ACCOUNT_PATH = f"{ACCOUNT_ARTIFACTS_PATH}/{ACCOUNT_AUTHOR}/{ACCOUNT_VERSION}/Account.cairo/Account.json"
ACCOUNT_ABI_PATH = f"{ACCOUNT_ARTIFACTS_PATH}/{ACCOUNT_AUTHOR}/{ACCOUNT_VERSION}/Account.cairo/Account_abi.json"
SALT = "0x99"
ACCOUNT_ADDRESS = "0x066a91d591d5ba09d37f21fd526242c1ddc6dc6b0ce72b2482a4c6c033114e3a"

TRANSACTION_VERSION = 0

PRIVATE_KEY = 123456789987654321
PUBLIC_KEY = private_to_stark_key(PRIVATE_KEY)

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Cleanup after tests finish."""

    # before test
    devnet_proc = run_devnet_in_background()

    yield

    # after test
    devnet_proc.kill()

def deploy_empty_contract():
    """Deploy sample contract with balance = 0."""
    return deploy(CONTRACT_PATH, inputs=["0"], salt=SALT)

def deploy_account_contract():
    """Deploy account contract."""
    return deploy(ACCOUNT_PATH, inputs=[str(PUBLIC_KEY)], salt=SALT)

def get_nonce():
    """Get nonce."""
    return call("get_nonce", ACCOUNT_ADDRESS, ACCOUNT_ABI_PATH)

def get_execute_calldata(call_array, calldata, nonce):
    """Get calldata for __execute__."""
    return [
        len(call_array),
        *[x for t in call_array for x in t],
        len(calldata),
        *calldata,
        int(nonce)
    ]

def str_to_felt(text):
    """Converts string to felt."""
    return int.from_bytes(bytes(text, "ascii"), "big")

def hash_multicall(sender, calls, nonce, max_fee):
    """desc"""
    hash_array = []

    for call_tuple in calls:
        call_elements = [call_tuple[0], call_tuple[1], compute_hash_on_elements(call_tuple[2])]
        hash_array.append(compute_hash_on_elements(call_elements))

    return compute_hash_on_elements([
        str_to_felt('StarkNet Transaction'),
        sender,
        compute_hash_on_elements(hash_array),
        nonce,
        max_fee,
        TRANSACTION_VERSION
    ])


def get_signature(message_hash):
    """Get signature from message hash and private key."""
    print(f"message hash {message_hash}")

    sig_r, sig_s = sign(message_hash, PRIVATE_KEY)
    return [str(sig_r), str(sig_s)]

def from_call_to_call_array(calls):
    """Transforms calls to call_array and calldata."""
    call_array = []
    calldata = []

    for call_tuple in calls:
        assert len(call_tuple) == 3, "Invalid call parameters"

        entry = (
            call_tuple[0],
            get_selector_from_name(call_tuple[1]),
            len(calldata),
            len(call_tuple[2])
        )
        call_array.append(entry)
        calldata.extend(call_tuple[2])

    return (call_array, calldata)

def adapt_inputs(execute_calldata):
    """Get stringified inputs from execute_calldata."""
    return [str(v) for v in execute_calldata]

def execute(calls, account=ACCOUNT_ADDRESS, nonce=None, max_fee=0):
    """Invoke __execute__ with correct calldata and signature."""
    if nonce is None:
        nonce = get_nonce()

    # get signature
    calls_with_selector = [
        (call[0], get_selector_from_name(call[1]), call[2]) for call in calls]
    message_hash = hash_multicall(
        int(account, 16), calls_with_selector, int(nonce), max_fee
    )
    signature = get_signature(message_hash)

    # get execute calldata
    (call_array, calldata) = from_call_to_call_array(calls)
    execute_calldata = get_execute_calldata(call_array, calldata, nonce)

    return invoke(
        "__execute__",
        inputs=adapt_inputs(execute_calldata),
        address=account,
        abi_path=ACCOUNT_ABI_PATH,
        signature=signature,
    )

@pytest.mark.account
def test_account_contract_deploy():
    """Test account contract deploy, public key and initial nonce value."""
    deploy_info = deploy_account_contract()
    assert deploy_info["address"] == ACCOUNT_ADDRESS

    deployed_public_key = call(
        "get_public_key", ACCOUNT_ADDRESS, ACCOUNT_ABI_PATH
    )
    assert int(deployed_public_key, 16) == PUBLIC_KEY

    nonce = get_nonce()
    assert nonce == "0"

@pytest.mark.account
def test_invoke_another_contract():
    """Test invoking another contract."""
    deploy_info = deploy_empty_contract()
    deploy_account_contract()
    to_address = int(deploy_info["address"], 16)

    # execute increase_balance call
    calls = [(to_address, "increase_balance", [10, 20])]
    tx_hash = execute(calls)

    assert_tx_status(tx_hash, "ACCEPTED_ON_L2")

    # check if nonce is increased
    nonce = get_nonce()
    assert nonce == "1"

    # check if balance is increased
    balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)
    assert balance == "30"


@pytest.mark.account
def test_multicall():
    """Test making multiple calls."""
    deploy_info = deploy_empty_contract()
    deploy_account_contract()
    to_address = int(deploy_info["address"], 16)

    # execute increase_balance calls
    calls = [
        (to_address, "increase_balance", [10, 20]),
        (to_address, "increase_balance", [30, 40])
    ]
    tx_hash = execute(calls)

    assert_tx_status(tx_hash, "ACCEPTED_ON_L2")

    # check if nonce is increased
    nonce = get_nonce()
    assert nonce == "1"

    # check if balance is increased
    balance = call("get_balance", deploy_info["address"], abi_path=ABI_PATH)
    assert balance == "100"
