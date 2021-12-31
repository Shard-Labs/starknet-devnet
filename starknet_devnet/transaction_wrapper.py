"""
Contains code for wrapping transactions.
"""

from abc import ABC, abstractmethod

from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType

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

    def set_transaction_failure(self, error_message: str):
        """Creates a new entry `failure_key` in the transaction object with the transaction failure reason data."""

        failure_key = "transaction_failure_reason"
        self.transaction[failure_key] = self.receipt[failure_key] = {
                "code": StarknetErrorCode.TRANSACTION_FAILED.name,
                "error_message": error_message,
                "tx_id": self.transaction_hash
        }


class DeployTransactionWrapper(TransactionWrapper):
    """Class for Deploy Transaction."""

    def __init__(self, internal_deploy, status, starknet):

        super().__init__()

        self.transaction_hash = hex(internal_deploy.to_external().calculate_hash(starknet.state.general_config))

        self.generate_transaction(
            internal_deploy,
            status,
            TransactionType.DEPLOY,
            constructor_calldata=[str(arg) for arg in internal_deploy.constructor_calldata],
            contract_address_salt=hex(internal_deploy.contract_address_salt)
        )


class InvokeTransactionWrapper(TransactionWrapper):
    """Class for Invoke Transaction."""

    def __init__(self, internal_transaction, status, starknet):

        super().__init__()

        self.transaction_hash = hex(internal_transaction.calculate_hash(starknet.state.general_config))

        self.generate_transaction(
            internal_transaction,
            status,
            TransactionType.INVOKE_FUNCTION,
            calldata=[str(arg) for arg in internal_transaction.calldata],
            entry_point_selector=str(internal_transaction.entry_point_selector)
        )
