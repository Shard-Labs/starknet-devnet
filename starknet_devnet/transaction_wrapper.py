"""
Contains code for wrapping transactions.
"""

from abc import ABC, abstractmethod
from starkware.starknet.business_logic.internal_transaction import InternalDeploy, InternalTransaction

from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo
from starkware.starknet.testing.starknet import Starknet

from .util import TxStatus, fixed_length_hex


class TransactionWrapper(ABC):
    """Transaction Wrapper base class."""

    @abstractmethod
    def __init__(
        self, internal_tx: InternalTransaction, status: TxStatus, tx_type: TransactionType, starknet: Starknet, **tx_details
    ):
        self.transaction = {}
        self.receipt = {}
        self.transaction_hash = fixed_length_hex(internal_tx.calculate_hash(starknet.state.general_config))
        self.transaction = {
            "status": status.name,
                "transaction": {
                    "contract_address": fixed_length_hex(internal_tx.contract_address),
                    "transaction_hash": self.transaction_hash,
                    "type": tx_type.name,
                    **tx_details
                },
                "transaction_index": 0 # always the first (and only) tx in the block
        }

    def generate_receipt(self, execution_info: StarknetTransactionExecutionInfo):
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

        assert self.transaction
        assert self.receipt
        failure_key = "transaction_failure_reason"
        self.transaction[failure_key] = self.receipt[failure_key] = {
            "code": StarknetErrorCode.TRANSACTION_FAILED.name,
            "error_message": error_message,
            "tx_id": self.transaction_hash
        }


class DeployTransactionWrapper(TransactionWrapper):
    """Wrapper of Deploy Transaction."""

    def __init__(self, internal_tx: InternalDeploy, status: TxStatus, starknet: Starknet):
        super().__init__(
            internal_tx.to_external(),
            status,
            TransactionType.DEPLOY,
            starknet,
            constructor_calldata=[str(arg) for arg in internal_tx.constructor_calldata],
            contract_address_salt=hex(internal_tx.contract_address_salt)
        )


class InvokeTransactionWrapper(TransactionWrapper):
    """Wrapper of Invoke Transaction."""

    def __init__(self, internal_tx: InvokeFunction, status: TxStatus, starknet: Starknet):
        super().__init__(
            internal_tx,
            status,
            TransactionType.INVOKE_FUNCTION,
            starknet,
            calldata=[str(arg) for arg in internal_tx.calldata],
            entry_point_selector=str(internal_tx.entry_point_selector)
        )
