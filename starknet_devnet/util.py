"""
Utility functions used across the project.
"""

from dataclasses import dataclass
from enum import Enum, auto
import argparse

from starkware.starkware_utils.error_handling import StarkException
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
    # Uncomment this once fork support is added
    # parser.add_argument(
    #     "--fork", "-f",
    #     type=_fork_url,
    #     help="Specify the network to fork: can be a URL (e.g. https://alpha-mainnet.starknet.io) " +
    #          "or network name (alpha or alpha-mainnet)",
    # )

    return parser.parse_args()

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
        self.cairo_usage = {}

@dataclass
class DummyExecutionInfo:
    """Used temporarily until contracts received from starknet.deploy include their own execution_info."""
    def __init__(self):
        self.call_info = DummyCallInfo()
        self.retdata = []
        self.internal_calls = []
        self.l2_to_l1_messages = []
