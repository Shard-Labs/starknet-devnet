from enum import Enum, auto
import argparse
from . import __version__

class TxStatus(Enum):
    """
    According to: https://www.cairo-lang.org/docs/hello_starknet/intro.html#interact-with-the-contract
    """

    PENDING = auto()
    """The transaction passed the validation and is waiting to be sent on-chain."""

    NOT_RECEIVED = auto()
    """The transaction has not been received yet (i.e., not written to storage"""

    RECEIVED = auto()
    """The transaction was received by the operator."""

    REJECTED = auto()
    """The transaction failed validation and thus was skipped."""

    ACCEPTED_ONCHAIN = auto()
    """The transaction was accepted on-chain."""


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000
def parse_args():
    parser = argparse.ArgumentParser(description="Run a local instance of Starknet devnet")
    parser.add_argument(
        "-v", "--version",
        help="Print the version",
        action="version",
        version=__version__
    )
    parser.add_argument(
        "--host",
        help=f"Specify the address to listen at; defaults to {DEFAULT_HOST} (use the address the program outputs on start)",
        default=DEFAULT_HOST
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        help=f"Specify the port to listen at; defaults to {DEFAULT_PORT}",
        default=DEFAULT_PORT
    )

    return parser.parse_args()