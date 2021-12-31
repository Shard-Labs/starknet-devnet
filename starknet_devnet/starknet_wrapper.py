"""
This module introduces `StarknetWrapper`, a wrapper class of
starkware.starknet.testing.starknet.Starknet.
"""

import time
from copy import deepcopy
from typing import Dict

from starkware.starknet.business_logic.internal_transaction import InternalDeploy
from starkware.starknet.business_logic.state import CarriedState
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Transaction
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo
from starkware.starkware_utils.error_handling import StarkException

from .origin import Origin
from .util import Choice, StarknetDevnetException, TxStatus, fixed_length_hex, DummyExecutionInfo
from .contract_wrapper import ContractWrapper
from .transaction_wrapper import TransactionWrapper, DeployTransactionWrapper, InvokeTransactionWrapper

class StarknetWrapper:
    """
    Wraps a Starknet instance and stores data to be returned by the server:
    contract states, transactions, blocks, storages.
    """
    def __init__(self, origin):
        self.origin: Origin = origin
        """Origin chain that this devnet was forked from."""

        self.__address2contract_wrapper: Dict[int, ContractWrapper] = {}
        """Maps contract address to contract wrapper."""

        self.__transaction_wrappers: Dict[int, TransactionWrapper] = {}
        """Maps transaction hash to transaction wrapper."""

        self.__hash2block = {}
        """Maps block hash to block."""

        self.__num2block: Dict[int, Dict] = {}
        """Maps block number to block (one transaction per block); holds only own blocks."""

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

        transaction_hash = await self.store_wrapper_transaction(
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

    def get_transaction_status(self, transaction_hash: str):
        """Returns the status of the transaction identified by `transaction_hash`."""

        tx_hash_int = int(transaction_hash,16)
        if tx_hash_int in self.__transaction_wrappers:

            transaction_wrapper = self.__transaction_wrappers[tx_hash_int]

            transaction = transaction_wrapper.transaction

            ret = {
                "tx_status": transaction["status"]
            }

            if "block_hash" in transaction:
                ret["block_hash"] = transaction["block_hash"]

            failure_key = "transaction_failure_reason"
            if failure_key in transaction:
                ret[failure_key] = transaction[failure_key]

            return ret

        return self.origin.get_transaction_status(transaction_hash)

    def get_transaction(self, transaction_hash: str):
        """Returns the transaction identified by `transaction_hash`."""

        tx_hash_int = int(transaction_hash,16)
        if tx_hash_int in self.__transaction_wrappers:

            return self.__transaction_wrappers[tx_hash_int].transaction

        return self.origin.get_transaction(transaction_hash)

    def get_transaction_receipt(self, transaction_hash: str):
        """Returns the transaction receipt of the transaction identified by `transaction_hash`."""

        tx_hash_int = int(transaction_hash,16)
        if tx_hash_int in self.__transaction_wrappers:

            return self.__transaction_wrappers[tx_hash_int].receipt

        return {
            "l2_to_l1_messages": [],
            "status": TxStatus.NOT_RECEIVED.name,
            "transaction_hash": transaction_hash
        }

    def get_number_of_blocks(self):
        """Returns the number of blocks stored so far."""
        return len(self.__num2block) + self.origin.get_number_of_blocks()

    async def __generate_block(self, transaction: dict, receipt: dict):
        """
        Generates a block and stores it to blocks and hash2block. The block contains just the passed transaction.
        The `transaction` dict should also contain a key `transaction`.
        """

        block_number = self.get_number_of_blocks()
        block_hash = hex(block_number)
        state_root = await self.__get_state_root()

        transaction["block_hash"] = receipt["block_hash"] = block_hash
        transaction["block_number"] = receipt["block_number"] = block_number

        block = {
            "block_hash": block_hash,
            "block_number": block_number,
            "parent_block_hash": self.__get_last_block()["block_hash"] if self.__num2block else "0x0",
            "state_root": state_root,
            "status": TxStatus.ACCEPTED_ON_L2.name,
            "timestamp": int(time.time()),
            "transaction_receipts": [receipt],
            "transactions": [transaction["transaction"]],
        }

        number_of_blocks = self.get_number_of_blocks()
        self.__num2block[number_of_blocks] = block
        self.__hash2block[int(block_hash, 16)] = block

    def __get_last_block(self):
        number_of_blocks = self.get_number_of_blocks()
        return self.get_block_by_number(number_of_blocks - 1)

    def get_block_by_hash(self, block_hash: str):
        """Returns the block identified either by its `block_hash`"""

        block_hash_int = int(block_hash, 16)
        if block_hash_int in self.__hash2block:
            return self.__hash2block[block_hash_int]
        return self.origin.get_block_by_hash(block_hash=block_hash)

    def get_block_by_number(self, block_number: int):
        """Returns the block whose block_number is provided"""
        if block_number is None:
            if self.__num2block:
                return self.__get_last_block()
            return self.origin.get_block_by_number(block_number)

        if block_number < 0:
            message = f"Block number must be a non-negative integer; got: {block_number}."
            raise StarknetDevnetException(message=message)

        if block_number >= self.get_number_of_blocks():
            message = f"Block number too high. There are currently {len(self.__num2block)} blocks; got: {block_number}."
            raise StarknetDevnetException(message=message)

        if block_number in self.__num2block:
            return self.__num2block[block_number]

        return self.origin.get_block_by_number(block_number)

    async def __store_transaction(self, transaction_wrapper: TransactionWrapper, error_message):

        if transaction_wrapper.transaction["status"] == TxStatus.REJECTED:
            transaction_wrapper.set_transaction_failure(error_message)
        else:
            await self.__generate_block(transaction_wrapper.transaction, transaction_wrapper.receipt)

        self.__transaction_wrappers[int(transaction_wrapper.transaction_hash,16)] = transaction_wrapper

        return transaction_wrapper.transaction_hash

    async def store_wrapper_transaction(self, transaction: Transaction, status: TxStatus,
        execution_info: StarknetTransactionExecutionInfo, error_message: str=None
    ):
        """Stores the provided data as a deploy transaction in `self.transactions`."""

        starknet = await self.get_starknet()

        if transaction.tx_type == TransactionType.DEPLOY:
            tx_wrapper = DeployTransactionWrapper(transaction,status,starknet)
        else:
            tx_wrapper = InvokeTransactionWrapper(transaction,status,starknet)

        tx_wrapper.generate_receipt(execution_info)

        return await self.__store_transaction(tx_wrapper, error_message)

    def get_code(self, contract_address: int) -> dict:
        """Returns a `dict` with `abi` and `bytecode` of the contract at `contract_address`."""
        if self.__is_contract_deployed(contract_address):
            contract_wrapper = self.__get_contract_wrapper(contract_address)
            return contract_wrapper.code
        return self.origin.get_code(contract_address)

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
        return self.origin.get_storage_at(self, contract_address, key)
