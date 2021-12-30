"""
Contains code for wrapping transactions.
"""

from abc import ABC, abstractmethod

from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.gateway.transaction_hash import calculate_transaction_hash

from .util import fixed_length_hex


class TransactionWrapper(ABC):
    """Transaction Wrapper base class."""

    @abstractmethod
    def __init__(self):
        self.transaction = {}
        self.receipt = {}
        self.transaction_hash = None

    def generate_transaction(self, internal_transaction, status, transaction_type, **transaction_details):
        """Creates the transaction object"""
        self.transaction = {
            "status": status.name,
                "transaction": {
                    "contract_address": fixed_length_hex(internal_transaction.contract_address),
                    "transaction_hash": self.transaction_hash,
                    "type": transaction_type.name,
                    **transaction_details
                },
                "transaction_index": 0 # always the first (and only) tx in the block
        }

    def generate_receipt(self, execution_info):
        """Creates the receipt for the transaction"""

        self.receipt = {
            "execution_resources": execution_info.call_info.cairo_usage,
            "l2_to_l1_messages": execution_info.l2_to_l1_messages,
            "status": self.transaction["status"],
            "transaction_hash": self.transaction_hash,
            "transaction_index": 0 # always the first (and only) tx in the block
        }

    def set_transaction_failure(self, failure_key: str, error_message: str):
        """Creates a new entry `failure_key` in the transaction object with the transaction failure reason data."""

        self.transaction[failure_key] = self.receipt[failure_key] = {
                "code": StarknetErrorCode.TRANSACTION_FAILED.name,
                "error_message": error_message,
                "tx_id": self.transaction["transaction"]["transaction_hash"]
        }


class DeployTransaction(TransactionWrapper):
    """Class for Deploy Transaction."""

    def __init__(self, internal_transaction, status, starknet):

        super().__init__()

        self.transaction_hash = hex(calculate_transaction_hash(
            tx_type=TransactionType.DEPLOY,
            contract_address=internal_transaction.contract_address,
            entry_point_selector=get_selector_from_name("constructor"),
            calldata=internal_transaction.constructor_calldata,
            chain_id=starknet.state.general_config.chain_id.value,
        ))

        self.generate_transaction(
            internal_transaction,
            status,
            TransactionType.DEPLOY,
            constructor_calldata=[str(arg) for arg in internal_transaction.constructor_calldata],
            contract_address_salt=hex(internal_transaction.contract_address_salt)
        )


class InvokeTransaction(TransactionWrapper):
    """Class for Invoke Transaction."""

    def __init__(self, internal_transaction, status, starknet):

        super().__init__()

        self.transaction_hash = hex(calculate_transaction_hash(
            TransactionType.INVOKE_FUNCTION,
            contract_address=internal_transaction.contract_address,
            entry_point_selector=internal_transaction.entry_point_selector,
            calldata=internal_transaction.calldata,
            chain_id=starknet.state.general_config.chain_id.value,
        ))

        self.generate_transaction(
            internal_transaction,
            status,
            TransactionType.INVOKE_FUNCTION,
            calldata=[str(arg) for arg in internal_transaction.calldata],
            entry_point_selector=str(internal_transaction.entry_point_selector)
        )
