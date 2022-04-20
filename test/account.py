"""
Account test functions and utilities.
"""


from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.signature import private_to_stark_key, sign
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.definitions.constants import TRANSACTION_VERSION, QUERY_VERSION

from .util import deploy, call, invoke, estimate_fee

ACCOUNT_ARTIFACTS_PATH = "starknet_devnet/accounts_artifacts"
ACCOUNT_AUTHOR = "OpenZeppelin"
ACCOUNT_VERSION = "0.1.0"

ACCOUNT_PATH = f"{ACCOUNT_ARTIFACTS_PATH}/{ACCOUNT_AUTHOR}/{ACCOUNT_VERSION}/Account.cairo/Account.json"
ACCOUNT_ABI_PATH = f"{ACCOUNT_ARTIFACTS_PATH}/{ACCOUNT_AUTHOR}/{ACCOUNT_VERSION}/Account.cairo/Account_abi.json"

PRIVATE_KEY = 123456789987654321
PUBLIC_KEY = private_to_stark_key(PRIVATE_KEY)

def deploy_account_contract(salt=None):
    """Deploy account contract."""
    return deploy(ACCOUNT_PATH, inputs=[str(PUBLIC_KEY)], salt=salt)

def get_nonce(account_address):
    """Get nonce."""
    return call("get_nonce", account_address, ACCOUNT_ABI_PATH)

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

def hash_multicall(sender, calls, nonce, max_fee, version):
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
        version
    ])


def get_signature(message_hash):
    """Get signature from message hash and private key."""
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

def get_execute_args(calls, account_address, nonce=None, max_fee=0, version=TRANSACTION_VERSION):
    """Returns signature and execute calldata"""

    if nonce is None:
        nonce = get_nonce(account_address)

    # get signature
    calls_with_selector = [
        (call[0], get_selector_from_name(call[1]), call[2]) for call in calls]
    message_hash = hash_multicall(
        sender=int(account_address, 16),
        calls=calls_with_selector,
        nonce=int(nonce),
        max_fee=max_fee,
        version=version
    )
    signature = get_signature(message_hash)

    # get execute calldata
    (call_array, calldata) = from_call_to_call_array(calls)
    execute_calldata = get_execute_calldata(call_array, calldata, nonce)

    return signature, execute_calldata

def get_estimated_fee(calls, account_address, nonce=None):
    """Get estmated fee."""
    signature, execute_calldata = get_execute_args(
        calls=calls,
        account_address=account_address,
        nonce=nonce,
        version=QUERY_VERSION
    )

    return estimate_fee(
        "__execute__",
        inputs=adapt_inputs(execute_calldata),
        address=account_address,
        abi_path=ACCOUNT_ABI_PATH,
        signature=signature,
    )

def execute(calls, account_address, nonce=None, max_fee=0):
    """Invoke __execute__ with correct calldata and signature."""
    signature, execute_calldata = get_execute_args(calls, account_address, nonce, max_fee)

    return invoke(
        "__execute__",
        inputs=adapt_inputs(execute_calldata),
        address=account_address,
        abi_path=ACCOUNT_ABI_PATH,
        signature=signature,
        max_fee=str(max_fee)
    )
