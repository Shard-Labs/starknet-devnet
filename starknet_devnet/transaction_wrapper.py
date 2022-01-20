"""
Contains code for wrapping transactions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from starkware.starknet.business_logic.internal_transaction import InternalDeploy, InternalInvokeFunction

from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo

from .util import TxStatus, fixed_length_hex

@dataclass
class TransactionDetails(ABC):
    """Base class for `DeployTransactionDetails` and `InvokeTransactionDetails`."""
    type: str
    contract_address: str
    transaction_hash: str

    def to_dict(self):
        """Get details in JSON/dict format."""
        return dict(self.__dict__)

@dataclass
class DeployTransactionDetails(TransactionDetails):
    """Transaction details of `DeployTransaction`."""
    constructor_calldata: List[str]
    contract_address_salt: str


@dataclass
class InvokeTransactionDetails(TransactionDetails):
    """Transcation details of `InvokeTransaction`."""
    calldata: List[str]
    signature: List[str]
    entry_point_selector: str

class TransactionWrapper(ABC):
    """Transaction Wrapper base class."""

    @abstractmethod
    def __init__(
        self, status: TxStatus, execution_info: StarknetTransactionExecutionInfo, tx_details: TransactionDetails
    ):
        self.transaction_hash = tx_details.transaction_hash

        self.transaction = {
            "status": status.name,
            "transaction": tx_details.to_dict(),
            "transaction_index": 0 # always the first (and only) tx in the block
        }

        self.receipt = {
            "execution_resources": execution_info.call_info.cairo_usage,
            "l2_to_l1_messages": execution_info.l2_to_l1_messages,
            "status": status.name,
            "transaction_hash": tx_details.transaction_hash,
            "transaction_index": 0 # always the first (and only) tx in the block
        }

    def set_block_data(self, block_hash: str, block_number: int):
        """Sets `block_hash` and `block_number` to the wrapped transaction and receipt."""
        self.transaction["block_hash"] = self.receipt["block_hash"] = block_hash
        self.transaction["block_number"] = self.receipt["block_number"] = block_number

    def set_failure_reason(self, error_message: str):
        """Sets the failure reason to transaction and receipt dicts."""
        assert error_message
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

    def __init__(self, internal_tx: InternalDeploy, status: TxStatus, execution_info: StarknetTransactionExecutionInfo):
        super().__init__(
            status,
            execution_info,
            DeployTransactionDetails(
                TransactionType.DEPLOY.name,
                contract_address=fixed_length_hex(internal_tx.contract_address),
                transaction_hash=fixed_length_hex(internal_tx.hash_value),
                constructor_calldata=[str(arg) for arg in internal_tx.constructor_calldata],
                contract_address_salt=hex(internal_tx.contract_address_salt)
            )
        )


class InvokeTransactionWrapper(TransactionWrapper):
    """Wrapper of Invoke Transaction."""

    def __init__(self, internal_tx: InternalInvokeFunction, status: TxStatus, execution_info: StarknetTransactionExecutionInfo):
        super().__init__(
            status,
            execution_info,
            InvokeTransactionDetails(
                TransactionType.INVOKE_FUNCTION.name,
                contract_address=fixed_length_hex(internal_tx.contract_address),
                transaction_hash=fixed_length_hex(internal_tx.hash_value),
                calldata=[str(arg) for arg in internal_tx.calldata],
                entry_point_selector=str(internal_tx.entry_point_selector),
                signature=[str(sig_part) for sig_part in internal_tx.signature]
            )
        )
