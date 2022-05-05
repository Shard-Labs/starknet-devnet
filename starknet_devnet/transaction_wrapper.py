"""
Contains code for wrapping transactions.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import List

from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
from starkware.starknet.business_logic.execution.objects import Event, L2ToL1MessageInfo
from starkware.starknet.services.api.feeder_gateway.response_objects import FunctionInvocation
from starkware.starknet.services.api.gateway.transaction import Deploy
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo, TransactionExecutionInfo

from .util import TxStatus, fixed_length_hex
from .constants import FAILURE_REASON_KEY

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
    class_hash: str


@dataclass
class InvokeTransactionDetails(TransactionDetails):
    """Transcation details of `InvokeTransaction`."""
    calldata: List[str]
    signature: List[str]
    entry_point_selector: str
    entry_point_type: str

def process_events(events: List[Event]):
    """Extract events and hex the content."""

    processed_events = []
    for event in events:
        processed_events.append({
            "from_address": hex(event.from_address),
            "data": [hex(d) for d in event.data],
            "keys": [hex(key) for key in event.keys]
        })
    return processed_events

class TransactionWrapper(ABC):
    """Transaction Wrapper base class."""

    # pylint: disable=too-many-arguments
    @abstractmethod
    def __init__(
        self,
        status: TxStatus,
        function_invocation: FunctionInvocation,
        tx_details: TransactionDetails,
        events: List[Event],
        l2_to_l1_messages: List[L2ToL1MessageInfo],
        actual_fee: int,
    ):
        self.transaction_hash = tx_details.transaction_hash

        self.transaction = {
            "status": status.name,
            "transaction": tx_details.to_dict(),
            "transaction_index": 0 # always the first (and only) tx in the block
        }

        self.receipt = {
            "actual_fee": hex(actual_fee),
            "execution_resources": function_invocation.execution_resources,
            "l2_to_l1_messages": l2_to_l1_messages,
            "events": process_events(events),
            "status": status.name,
            "transaction_hash": tx_details.transaction_hash,
            "transaction_index": 0 # always the first (and only) tx in the block
        }

        if status is not TxStatus.REJECTED:
            self.trace = {
                "function_invocation": function_invocation.dump(),
                "signature": tx_details.to_dict().get("signature", [])
            }

    def set_block_data(self, block_hash: str, block_number: int):
        """Sets `block_hash` and `block_number` to the wrapped transaction and receipt."""
        self.transaction["block_hash"] = self.receipt["block_hash"] = block_hash
        self.transaction["block_number"] = self.receipt["block_number"] = block_number

    def get_receipt_block_variant(self):
        """
        Receipt is a part of get_block response, but somewhat modified.
        This method returns the modified version.
        """
        receipt = deepcopy(self.receipt)
        del receipt["status"]
        return receipt

    def set_failure_reason(self, error_message: str):
        """Sets the failure reason to transaction and receipt dicts."""
        assert error_message
        assert self.transaction
        assert self.receipt

        self.transaction[FAILURE_REASON_KEY] = self.receipt[FAILURE_REASON_KEY] = {
            "code": StarknetErrorCode.TRANSACTION_FAILED.name,
            "error_message": error_message,
            "tx_id": self.transaction_hash
        }


class DeployTransactionWrapper(TransactionWrapper):
    """Wrapper of Deploy Transaction."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        transaction: Deploy,
        contract_address: int,
        tx_hash: int,
        status: TxStatus,
        execution_info: StarknetTransactionExecutionInfo,
        contract_hash: bytes
    ):
        super().__init__(
            status,
            execution_info.call_info,
            DeployTransactionDetails(
                TransactionType.DEPLOY.name,
                contract_address=fixed_length_hex(contract_address),
                transaction_hash=fixed_length_hex(tx_hash),
                constructor_calldata=[hex(arg) for arg in transaction.constructor_calldata],
                contract_address_salt=hex(transaction.contract_address_salt),
                class_hash=fixed_length_hex(int.from_bytes(contract_hash, "big"))
            ),
            events=execution_info.raw_events,
            l2_to_l1_messages=execution_info.l2_to_l1_messages,
            actual_fee=0
        )


class InvokeTransactionWrapper(TransactionWrapper):
    """Wrapper of Invoke Transaction."""

    def __init__(self, internal_tx: InternalInvokeFunction, status: TxStatus, execution_info: TransactionExecutionInfo):
        call_info = execution_info.call_info
        if status is not TxStatus.REJECTED:
            call_info = FunctionInvocation.from_internal_version(call_info)
        super().__init__(
            status,
            call_info,
            InvokeTransactionDetails(
                TransactionType.INVOKE_FUNCTION.name,
                contract_address=fixed_length_hex(internal_tx.contract_address),
                transaction_hash=fixed_length_hex(internal_tx.hash_value),
                calldata=[hex(arg) for arg in internal_tx.calldata],
                entry_point_selector=fixed_length_hex(internal_tx.entry_point_selector),
                entry_point_type=internal_tx.entry_point_type.name,
                signature=[hex(sig_part) for sig_part in internal_tx.signature]
            ),
            events=execution_info.get_sorted_events(),
            l2_to_l1_messages=execution_info.get_sorted_l2_to_l1_messages(),
            actual_fee=execution_info.actual_fee
        )
