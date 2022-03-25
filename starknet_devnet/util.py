"""
Utility functions used across the project.
"""

from dataclasses import dataclass
from enum import Enum, auto
import argparse
import sys

from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.business_logic.state import CarriedState
from starkware.starknet.definitions.general_config import StarknetGeneralConfig

from . import __version__

class TxStatus(Enum):
    """
    According to: https://www.cairo-lang.org/docs/hello_starknet/intro.html#interact-with-the-contract
    """

    NOT_RECEIVED = auto()
    """The transaction has not been received yet (i.e. not written to storage)."""

    RECEIVED = auto()
    """The transaction was received by the operator."""

    PENDING = auto()
    """The transaction passed the validation and entered the pending block."""

    REJECTED = auto()
    """The transaction failed validation and thus was skipped."""

    ACCEPTED_ON_L2 = auto()
    """The transaction passed the validation and entered an actual created block."""

    ACCEPTED_ON_L1 = auto()
    """The transaction was accepted on-chain."""


class Choice(Enum):
    """Enumerates ways of interacting with a Starknet function."""
    CALL = "call"
    INVOKE = "invoke"


def custom_int(arg: str) -> str:
    """
    Converts the argument to an integer.
    Conversion base is 16 if `arg` starts with `0x`, otherwise `10`.
    """
    base = 16 if arg.startswith("0x") else 10
    return int(arg, base)

def fixed_length_hex(arg: int) -> str:
    """
    Converts the int input to a hex output of fixed length
    """
    return f"0x{arg:064x}"

# Uncomment this once fork support is added
# def _fork_url(name: str):
#     """
#     Return the URL corresponding to the provided name.
#     If it's not one of predefined names, assumes it is already a URL.
#     """
#     if name in ["alpha", "alpha-goerli"]:
#         return "https://alpha4.starknet.io"
#     if name == "alpha-mainnet":
#         return "https://alpha-mainnet.starknet.io"
#     # otherwise a URL; perhaps check validity
#     return name

class DumpOn(Enum):
    """Enumerate possible dumping frequencies."""
    EXIT = auto()
    TRANSACTION = auto()

DUMP_ON_OPTIONS = [e.name.lower() for e in DumpOn]
DUMP_ON_OPTIONS_STRINGIFIED = ", ".join(DUMP_ON_OPTIONS)

def parse_dump_on(option: str):
    """Parse dumping frequency option."""
    if option in DUMP_ON_OPTIONS:
        return DumpOn[option.upper()]
    sys.exit(f"Error: Invalid --dump-on option: {option}. Valid options: {DUMP_ON_OPTIONS_STRINGIFIED}")

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000
def parse_args():
    """
    Parses CLI arguments.
    """
    parser = argparse.ArgumentParser(description="Run a local instance of Starknet Devnet")
    parser.add_argument(
        "-v", "--version",
        help="Print the version",
        action="version",
        version=__version__
    )
    parser.add_argument(
        "--host",
        help=f"Specify the address to listen at; defaults to {DEFAULT_HOST}" +
             "(use the address the program outputs on start)",
        default=DEFAULT_HOST
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        help=f"Specify the port to listen at; defaults to {DEFAULT_PORT}",
        default=DEFAULT_PORT
    )
    parser.add_argument(
        "--load-path",
        help="Specify the path from which the state is loaded on startup"
    )
    parser.add_argument(
        "--dump-path",
        help="Specify the path to dump to"
    )
    parser.add_argument(
        "--dump-on",
        help=f"Specify when to dump; can dump on: {DUMP_ON_OPTIONS_STRINGIFIED}",
        type=parse_dump_on
    )
    # Uncomment this once fork support is added
    # parser.add_argument(
    #     "--fork", "-f",
    #     type=_fork_url,
    #     help="Specify the network to fork: can be a URL (e.g. https://alpha-mainnet.starknet.io) " +
    #          "or network name (alpha or alpha-mainnet)",
    # )

    args = parser.parse_args()
    if args.dump_on and not args.dump_path:
        sys.exit("Error: --dump-path required if --dump-on present")

    return args

class StarknetDevnetException(StarkException):
    """
    Exception raised across the project.
    Indicates the raised issue is devnet-related.
    """
    def __init__(self, code=500, message=None):
        super().__init__(code=code, message=message)

@dataclass
class DummyCallInfo:
    """Used temporarily until contracts received from starknet.deploy include their own execution_info.call_info"""
    def __init__(self):
        self.execution_resources = {}

@dataclass
class DummyExecutionInfo:
    """Used temporarily until contracts received from starknet.deploy include their own execution_info."""
    def __init__(self):
        self.call_info = DummyCallInfo()
        self.retdata = []
        self.internal_calls = []
        self.l2_to_l1_messages = []

def enable_pickling():
    """
    Extends the `StarknetContract` class to enable pickling.
    """
    def contract_getstate(self):
        return self.__dict__

    def contract_setstate(self, state):
        self.__dict__ = state

    StarknetContract.__getstate__ = contract_getstate
    StarknetContract.__setstate__ = contract_setstate

def generate_storage_diff(previous_storage_updates, storage_updates):
    """
    Returns storage diff between previous and current storage updates
    """
    if not previous_storage_updates:
        return []

    storage_diff = []

    for storage_key, leaf in storage_updates.items():
        previous_leaf = previous_storage_updates.get(storage_key)

        if previous_leaf is None or previous_leaf.value != leaf.value:
            storage_diff.append({
                "key": hex(storage_key),
                "value": hex(leaf.value)
            })

    return storage_diff


def generate_state_update(previous_state: CarriedState, current_state: CarriedState):
    """
    Returns roots, deployed contracts and storage diffs between 2 states
    """
    deployed_contracts = []
    storage_diffs = {}

    for contract_address in current_state.contract_states.keys():
        if contract_address not in previous_state.contract_states:
            deployed_contracts.append({
                "address": fixed_length_hex(contract_address),
                "contract_hash": current_state.contract_states[contract_address].state.contract_hash.hex()
            })
        else:
            previous_storage_updates = previous_state.contract_states[contract_address].storage_updates
            storage_updates = current_state.contract_states[contract_address].storage_updates
            storage_diff = generate_storage_diff(previous_storage_updates, storage_updates)

            if len(storage_diff) > 0:
                contract_address_hexed = fixed_length_hex(contract_address)
                storage_diffs[contract_address_hexed] = storage_diff

    new_root = current_state.shared_state.contract_states.root.hex()
    old_root = previous_state.shared_state.contract_states.root.hex()

    return {
        "new_root": new_root,
        "old_root": old_root,
        "state_diff": {
            "deployed_contracts": deployed_contracts,
            "storage_diffs": storage_diffs
        }
    }

DEFAULT_GENERAL_CONFIG = StarknetGeneralConfig.load({
    "event_commitment_tree_height": 64,
    "global_state_commitment_tree_height": 251,
    'gas_price': 100000000000,
    'starknet_os_config': {
        'chain_id': 'TESTNET',
        'fee_token_address': '0x20abcf49dad3e9813d65bf1b8d54c5a0c9e6049a3027bd8c2ab315475c0a5c1'
    },
    'contract_storage_commitment_tree_height': 251,
    'cairo_resource_fee_weights': {
        'n_steps': 0.05,
        'pedersen_builtin': 0.4,
        'range_check_builtin': 0.4,
        'ecdsa_builtin': 25.6,
        'bitwise_builtin': 12.8,
        'output_builtin': 0.0,
        'ec_op_builtin': 0.0
    }, 'invoke_tx_max_n_steps': 1000000,
    'sequencer_address': '0x37b2cd6baaa515f520383bee7b7094f892f4c770695fc329a8973e841a971ae',
    'tx_version': 0,
    'tx_commitment_tree_height': 64
})
