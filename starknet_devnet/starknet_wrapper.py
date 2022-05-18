"""
This module introduces `StarknetWrapper`, a wrapper class of
starkware.starknet.testing.starknet.Starknet.
"""

import dataclasses
from copy import deepcopy
from typing import Dict

import dill as pickle
from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
from starkware.starknet.business_logic.state.state import CarriedState
from starkware.starknet.services.api.gateway.contract_address import calculate_contract_address
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Deploy
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.business_logic.transaction_fee import calculate_tx_fee_by_cairo_usage

from .origin import NullOrigin, Origin
from .general_config import DEFAULT_GENERAL_CONFIG
from .util import (
    StarknetDevnetException, TxStatus, DummyExecutionInfo,
    enable_pickling, generate_state_update
)
from .contract_wrapper import ContractWrapper, call_internal_tx
from .transaction_wrapper import DeployTransactionWrapper, InvokeTransactionWrapper, TransactionWrapper
from .postman_wrapper import DevnetL1L2
from .transactions import DevnetTransactions
from .contracts import DevnetContracts
from .blocks import DevnetBlocks
from .block_info_generator import BlockInfoGenerator

enable_pickling()

@dataclasses.dataclass
class DevnetConfig:
    """Configuration for the devnet."""
    lite_mode_block_hash: bool = False
    lite_mode_deploy_hash: bool = False

#pylint: disable=too-many-instance-attributes
class StarknetWrapper:
    """
    Wraps a Starknet instance and stores data to be returned by the server:
    contract states, transactions, blocks, storages.
    """

    def __init__(self, config: DevnetConfig):
        self.origin: Origin = NullOrigin()
        """Origin chain that this devnet was forked from."""

        self.transactions = DevnetTransactions(self.origin)

        self.contracts = DevnetContracts(self.origin)

        self.blocks = DevnetBlocks(self.origin, lite=config.lite_mode_block_hash)

        self.l1l2 = DevnetL1L2()

        self.__starknet = None

        self.__current_carried_state = None

        self.config = config

        self.block_info_generator = BlockInfoGenerator()

    @staticmethod
    def load(path: str) -> "StarknetWrapper":
        """Load a serialized instance of this class from `path`."""
        with open(path, "rb") as file:
            return pickle.load(file)

    async def __preserve_current_state(self, state: CarriedState):
        self.__current_carried_state = deepcopy(state)
        self.__current_carried_state.shared_state = state.shared_state

    async def __get_starknet(self):
        """
        Returns the underlying Starknet instance, creating it first if necessary.
        """
        if not self.__starknet:
            self.__starknet = await Starknet.empty(general_config=DEFAULT_GENERAL_CONFIG)
            await self.__preserve_current_state(self.__starknet.state.state)

        return self.__starknet

    async def __get_state(self):
        """
        Returns the StarknetState of the underlyling Starknet instance,
        creating the instance first if necessary.
        """
        starknet = await self.__get_starknet()
        return starknet.state

    async def __update_state(self):
        if not self.config.lite_mode_block_hash:
            previous_state = self.__current_carried_state
            assert previous_state is not None
            current_carried_state = (await self.__get_state()).state
            state = await self.__get_state()

            current_carried_state.block_info = self.block_info_generator.next_block(
                block_info=current_carried_state.block_info,
                general_config=state.general_config
            )

            updated_shared_state = await current_carried_state.shared_state.apply_state_updates(
                ffc=current_carried_state.ffc,
                previous_carried_state=previous_state,
                current_carried_state=current_carried_state
            )
            self.__starknet.state.state.shared_state = updated_shared_state
            await self.__preserve_current_state(self.__starknet.state.state)

            return generate_state_update(previous_state, current_carried_state)

    async def __get_state_root(self):
        state = await self.__get_state()
        return state.state.shared_state.contract_states.root

    async def __store_transaction(
        self, tx_wrapper: TransactionWrapper, state_update: Dict, error_message: str=None
    ) -> None:
        """
        Stores the provided data as a deploy transaction in `self.transactions`.
        Generates a new block
        """

        if tx_wrapper.transaction["status"] == TxStatus.REJECTED.name:
            assert error_message, "error_message must be present if tx rejected"
            tx_wrapper.set_failure_reason(error_message)
        else:
            state = await self.__get_state()
            state_root = await self.__get_state_root()

            block_hash, block_number = await self.blocks.generate(
                tx_wrapper,
                state,
                state_root,
                state_update=state_update,
            )
            tx_wrapper.set_block_data(block_hash, block_number)

        self.transactions.store(tx_wrapper)

    def set_config(self, config: DevnetConfig):
        """
        Sets the configuration of the devnet.
        """
        self.config = config
        self.blocks.lite = config.lite_mode_block_hash

    async def deploy(self, deploy_transaction: Deploy):
        """
        Deploys the contract specified with `transaction`.
        Returns (contract_address, transaction_hash).
        """

        state = await self.__get_state()
        contract_definition = deploy_transaction.contract_definition
        if self.config.lite_mode_deploy_hash:
            tx_hash = self.transactions.get_count()
        else:
            tx_hash = deploy_transaction.calculate_hash(state.general_config)

        starknet = await self.__get_starknet()

        try:
            contract = await starknet.deploy(
                contract_def=contract_definition,
                constructor_calldata=deploy_transaction.constructor_calldata,
                contract_address_salt=deploy_transaction.contract_address_salt
            )
            contract_address = contract.contract_address
            execution_info = contract.deploy_execution_info
            error_message = None
            status = TxStatus.ACCEPTED_ON_L2

            self.contracts.store(contract.contract_address, ContractWrapper(contract, contract_definition))
            state_update = await self.__update_state()
        except StarkException as err:
            error_message = err.message
            status = TxStatus.REJECTED
            execution_info = DummyExecutionInfo()
            state_update = None

            contract_address = calculate_contract_address(
                caller_address=0,
                constructor_calldata=deploy_transaction.constructor_calldata,
                salt=deploy_transaction.contract_address_salt,
                contract_definition=deploy_transaction.contract_definition
            )

        tx_wrapper = DeployTransactionWrapper(
            transaction=deploy_transaction,
            contract_address=contract_address,
            tx_hash=tx_hash,
            status=status,
            execution_info=execution_info,
            contract_hash=state.state.contract_states[contract_address].state.contract_hash,
        )

        await self.__store_transaction(
            tx_wrapper=tx_wrapper,
            state_update=state_update,
            error_message=error_message,
        )

        return contract_address, tx_hash

    async def invoke(self, transaction: InvokeFunction):
        """Perform invoke according to specifications in `transaction`."""
        state = await self.__get_state()
        invoke_transaction: InternalInvokeFunction = InternalInvokeFunction.from_external(transaction, state.general_config)

        try:
            # This check might not be needed in future versions which will interact with the token contract
            if invoke_transaction.max_fee: # handle only if non-zero
                actual_fee = await self.calculate_actual_fee(transaction)
                if actual_fee > invoke_transaction.max_fee:
                    message = f"Actual fee exceeded max fee.\n{actual_fee} > {invoke_transaction.max_fee}"
                    raise StarknetDevnetException(message=message)

            contract_wrapper = self.contracts.get_by_address(invoke_transaction.contract_address)
            adapted_result, execution_info = await contract_wrapper.invoke(
                entry_point_selector=invoke_transaction.entry_point_selector,
                calldata=invoke_transaction.calldata,
                signature=invoke_transaction.signature,
                caller_address=invoke_transaction.caller_address,
                max_fee=invoke_transaction.max_fee
            )
            status = TxStatus.ACCEPTED_ON_L2
            error_message = None
            state_update = await self.__update_state()
        except StarkException as err:
            error_message = err.message
            status = TxStatus.REJECTED
            execution_info = DummyExecutionInfo()
            adapted_result = []
            state_update = None

        tx_wrapper = InvokeTransactionWrapper(invoke_transaction, status, execution_info)

        await self.__store_transaction(
            tx_wrapper=tx_wrapper,
            state_update=state_update,
            error_message=error_message
        )

        return transaction.contract_address, invoke_transaction.hash_value, { "result": adapted_result }

    async def call(self, transaction: InvokeFunction):
        """Perform call according to specifications in `transaction`."""
        contract_wrapper = self.contracts.get_by_address(transaction.contract_address)

        adapted_result = await contract_wrapper.call(
            entry_point_selector=transaction.entry_point_selector,
            calldata=transaction.calldata,
            signature=transaction.signature,
            caller_address=0,
            max_fee=transaction.max_fee
        )

        return { "result": adapted_result }

    async def get_storage_at(self, contract_address: int, key: int) -> str:
        """
        Returns the storage identified by `key`
        from the contract at `contract_address`.
        """
        state = await self.__get_state()
        contract_states = state.state.contract_states

        contract_state = contract_states[contract_address]
        if key in contract_state.storage_updates:
            return hex(contract_state.storage_updates[key].value)
        return self.origin.get_storage_at(contract_address, key)

    async def load_messaging_contract_in_l1(self, network_url: str, contract_address: str, network_id: str) -> dict:
        """Loads the messaging contract at `contract_address`"""
        starknet = await self.__get_starknet()
        return self.l1l2.load_l1_messaging_contract(starknet, network_url, contract_address, network_id)

    async def postman_flush(self) -> dict:
        """Handles all pending L1 <> L2 messages and sends them to the other layer. """

        state = await self.__get_state()
        return await self.l1l2.flush(state)

    async def calculate_actual_fee(self, external_tx: InvokeFunction):
        """Calculates actual fee"""
        state = await self.__get_state()
        internal_tx = InternalInvokeFunction.from_external_query_tx(external_tx, state.general_config)

        execution_info = await call_internal_tx(state.copy(), internal_tx)

        actual_fee = calculate_tx_fee_by_cairo_usage(
            general_config=state.general_config,
            cairo_resource_usage=execution_info.call_info.execution_resources.to_dict(),
            l1_gas_usage=0,
            gas_price=state.general_config.min_gas_price
        )

        return actual_fee

    def increase_block_time(self, time_s: int):
        """Increases the block time by `time_s`."""
        self.block_info_generator.increase_time(time_s)

    def set_block_time(self, time_s: int):
        """Sets the block time to `time_s`."""
        self.block_info_generator.set_next_block_time(time_s)
