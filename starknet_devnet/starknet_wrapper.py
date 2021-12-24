"""
This module introduces `StarknetWrapper`, a wrapper class of
starkware.starknet.testing.starknet.Starknet.
"""

import time
from copy import deepcopy
from typing import Dict
from starkware.starknet.business_logic.internal_transaction import InternalDeploy

from starkware.starknet.business_logic.state import CarriedState
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.error_handling import StarkException

from .util import Choice, StarknetDevnetException, TxStatus, fixed_length_hex, DummyExecutionInfo
from .contract_wrapper import ContractWrapper


def _generate_transaction_basis(contract_address: str, status: TxStatus, transaction_hash: str, **transaction_details: dict):
    return {
        "status": status.name,
        "transaction": {
            "contract_address": fixed_length_hex(contract_address),
            "transaction_hash": transaction_hash,
            **transaction_details
        },
        "transaction_index": 0 # always the first (and only) tx in the block
    }

def _generate_transaction_receipt_basis(status: TxStatus, transaction_hash: str, execution_info: StarknetTransactionExecutionInfo):
    return {
        "execution_resources": execution_info.call_info.cairo_usage,
        "l2_to_l1_messages": execution_info.l2_to_l1_messages,
        "status": status.name,
        "transaction_hash": transaction_hash,
        "transaction_index": 0 # always the first (and only) tx in the block
    }

class StarknetWrapper:
    """
    Wraps a Starknet instance and stores data to be returned by the server:
    contract states, transactions, blocks, storages.
    """
    def __init__(self):
        self.__address2contract_wrapper: Dict[int, ContractWrapper] = {}
        """Maps contract address to contract wrapper."""

        self.__transactions = []
        """A chronological list of transactions."""

        self.__transaction_receipts = []
        """A chronological list of transaction receipts."""

        self.__hash2block = {}
        """Maps block hash to block."""

        self.__blocks = []
        """A chronological list of blocks (one transaction per block)."""

        self.__starknet = None

        self.__current_carried_state = None

    async def __preserve_current_state(self, state: CarriedState):
        self.__current_carried_state = deepcopy(state)
        self.__current_carried_state.shared_state = state.shared_state

    async def get_starknet(self):
        """
        Returns the underlying Starknet instance, creating it first if necessary.
        """
        if not self.__starknet:
            self.__starknet = await Starknet.empty()
            await self.__preserve_current_state(self.__starknet.state.state)
        return self.__starknet

    async def get_state(self):
        """
        Returns the StarknetState of the underlyling Starknet instance,
        creating the instance first if necessary.
        """
        starknet = await self.get_starknet()
        return starknet.state

    async def __update_state(self):
        previous_state = self.__current_carried_state
        assert previous_state is not None
        current_carried_state = (await self.get_state()).state
        updated_shared_state = await current_carried_state.shared_state.apply_state_updates(
            ffc=current_carried_state.ffc,
            previous_carried_state=previous_state,
            current_carried_state=current_carried_state
        )
        self.__starknet.state.state.shared_state = updated_shared_state
        await self.__preserve_current_state(self.__starknet.state.state)
        # await self.preserve_carried_state(current_carried_state)

    async def __get_state_root(self):
        state = await self.get_state()
        return state.state.shared_state.contract_states.root.hex()

    def __is_contract_deployed(self, address: int) -> bool:
        return address in self.__address2contract_wrapper

    def __get_contract_wrapper(self, address: int) -> ContractWrapper:
        if not self.__is_contract_deployed(address):
            message = f"No contract at the provided address ({fixed_length_hex(address)})."
            raise StarknetDevnetException(message=message)

        return self.__address2contract_wrapper[address]

    async def deploy(self, transaction: InternalDeploy):
        """
        Deploys the contract specified with `transaction` and returns tx hash in hex.
        """

        starknet = await self.get_starknet()
        status = TxStatus.ACCEPTED_ON_L2
        error_message = None

        try:
            contract = await starknet.deploy(
                contract_def=transaction.contract_definition,
                constructor_calldata=transaction.constructor_calldata,
                contract_address_salt=transaction.contract_address_salt
            )
        except StarkException as err:
            error_message = err.message
            status = TxStatus.REJECTED

        transaction_hash = await self.__store_deploy_transaction(
            transaction,
            status=status,
            execution_info=DummyExecutionInfo(),
            error_message=error_message
        )

        await self.__update_state()
        self.__address2contract_wrapper[contract.contract_address] = ContractWrapper(contract, transaction.contract_definition)
        return transaction_hash

    async def call_or_invoke(self, choice: Choice, specifications: InvokeFunction):
        """
        Performs `ContractWrapper.call_or_invoke` on the contract at `contract_address`.
        If `choice` is INVOKE, updates the state.
        Returns a tuple of:
        - `dict` with `"result"`, holding the adapted result
        - `execution_info`
        """
        contract_wrapper = self.__get_contract_wrapper(specifications.contract_address)
        adapted_result, execution_info = await contract_wrapper.call_or_invoke(
            choice,
            entry_point_selector=specifications.entry_point_selector,
            calldata=specifications.calldata,
            signature=specifications.signature
        )

        if choice == Choice.INVOKE:
            await self.__update_state()

        return { "result": adapted_result }, execution_info

    def __is_transaction_hash_legal(self, transaction_hash_int: int) -> bool:
        return 0 <= transaction_hash_int < len(self.__transactions)

    def get_transaction_status(self, transaction_hash: str):
        """Returns the status of the transaction identified by `transaction_hash`."""

        transaction_hash_int = int(transaction_hash, 16)

        if self.__is_transaction_hash_legal(transaction_hash_int):
            transaction = self.__transactions[transaction_hash_int]
            ret = {
                "tx_status": transaction["status"]
            }

            if "block_hash" in transaction:
                ret["block_hash"] = transaction["block_hash"]

            failure_key = "transaction_failure_reason"
            if failure_key in transaction:
                ret[failure_key] = transaction[failure_key]

            return ret

        return {
            "tx_status": TxStatus.NOT_RECEIVED.name
        }

    def get_transaction(self, transaction_hash: str):
        """Returns the transaction identified by `transaction_hash`."""

        transaction_hash_int = int(transaction_hash, 16)
        if self.__is_transaction_hash_legal(transaction_hash_int):
            return self.__transactions[transaction_hash_int]
        return {
            "status": TxStatus.NOT_RECEIVED.name,
            "transaction_hash": transaction_hash
        }

    def get_transaction_receipt(self, transaction_hash: str):
        """Returns the transaction receipt of the transaction identified by `transaction_hash`."""

        transaction_hash_int = int(transaction_hash, 16)
        if self.__is_transaction_hash_legal(transaction_hash_int):
            return self.__transaction_receipts[transaction_hash_int]
        return {
            "l2_to_l1_messages": [],
            "status": TxStatus.NOT_RECEIVED.name,
            "transaction_hash": transaction_hash
        }

    async def __generate_block(self, transaction: dict, receipt: dict):
        """
        Generates a block and stores it to blocks and hash2block. The block contains just the passed transaction.
        The `transaction` dict should also contain a key `transaction`.
        """

        block_number = len(self.__blocks)
        block_hash = hex(block_number)
        state_root = await self.__get_state_root()

        transaction["block_hash"] = receipt["block_hash"] = block_hash
        transaction["block_number"] = receipt["block_number"] = block_number

        block = {
            "block_hash": block_hash,
            "block_number": block_number,
            "parent_block_hash": self.__blocks[-1]["block_hash"] if self.__blocks else "0x0",
            "state_root": state_root,
            "status": TxStatus.ACCEPTED_ON_L2.name,
            "timestamp": int(time.time()),
            "transaction_receipts": [receipt],
            "transactions": [transaction["transaction"]],
        }

        self.__blocks.append(block)
        self.__hash2block[int(block_hash, 16)] = block

    def get_block(self, block_hash: str=None, block_number: int=None):
        """Returns the block identified either by its `block_hash` or `block_number`."""

        if block_hash is not None and block_number is not None:
            message = "Ambiguous criteria: only one of (block number, block hash) can be provided."
            raise StarknetDevnetException(message=message)

        if block_hash is not None:
            block_hash_int = int(block_hash, 16)
            if block_hash_int in self.__hash2block:
                return self.__hash2block[block_hash_int]
            message = f"Block hash not found; got: {block_hash}."
            raise StarknetDevnetException(message=message)

        if block_number is not None:
            if block_number < 0:
                message = f"Block number must be a non-negative integer; got: {block_number}."
                raise StarknetDevnetException(message=message)

            if block_number >= len(self.__blocks):
                message = f"Block number too high. There are currently {len(self.__blocks)} blocks; got: {block_number}."
                raise StarknetDevnetException(message=message)

            return self.__blocks[block_number]

        # no block identifier means latest block
        if self.__blocks:
            return self.__blocks[-1]
        message = "Requested the latest block, but there are no blocks so far."
        raise StarknetDevnetException(message=message)

    async def __store_transaction(self, contract_address: str, status: TxStatus,
        execution_info: StarknetTransactionExecutionInfo, error_message: str=None, **transaction_details: dict
    ):
        new_id = len(self.__transactions)
        hex_new_id = hex(new_id)

        transaction = _generate_transaction_basis(contract_address, status, hex_new_id, **transaction_details)
        receipt = _generate_transaction_receipt_basis(status, hex_new_id, execution_info)

        if status == TxStatus.REJECTED:
            failure_key = "transaction_failure_reason"
            transaction[failure_key] = receipt[failure_key] = {
                "code": StarknetErrorCode.TRANSACTION_FAILED.name,
                "error_message": error_message,
                "tx_id": new_id
            }
        else:
            await self.__generate_block(transaction, receipt)

        self.__transactions.append(transaction)
        self.__transaction_receipts.append(receipt)
        return hex_new_id

    async def __store_deploy_transaction(self, transaction: InternalDeploy, status: TxStatus,
        execution_info: StarknetTransactionExecutionInfo, error_message: str=None
    ):
        """Stores the provided data as a deploy transaction in `self.transactions`."""
        return await self.__store_transaction(
            transaction.contract_address,
            status,
            execution_info,
            error_message,
            type=TransactionType.DEPLOY.name,
            constructor_calldata=[str(arg) for arg in transaction.constructor_calldata],
            contract_address_salt=hex(transaction.contract_address_salt)
        )

    async def store_invoke_transaction(self, transaction: InvokeFunction, status: TxStatus,
        execution_info: StarknetTransactionExecutionInfo, error_message: str=None
    ):
        """Stores the provided data as an invoke transaction in `self.transactions`."""
        return await self.__store_transaction(
            transaction.contract_address,
            status,
            execution_info,
            error_message,
            type=TransactionType.INVOKE_FUNCTION.name,
            calldata=[str(arg) for arg in transaction.calldata],
            entry_point_selector=str(transaction.entry_point_selector),
            # entry_point_type
        )

    def get_code(self, contract_address: int) -> dict:
        """Returns a `dict` with `abi` and `bytecode` of the contract at `contract_address`."""
        if self.__is_contract_deployed(contract_address):
            contract_wrapper = self.__get_contract_wrapper(contract_address)
            return contract_wrapper.code
        return {
            "abi": {},
            "bytecode": []
        }

    async def get_storage_at(self, contract_address: int, key: int) -> str:
        """
        Returns the storage identified by `key`
        from the contract at `contract_address`.
        """
        state = await self.get_state()
        contract_states = state.state.contract_states

        state = contract_states[contract_address]
        if key in state.storage_updates:
            return hex(state.storage_updates[key].value)
        return hex(0)
