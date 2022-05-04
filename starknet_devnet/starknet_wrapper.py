"""
This module introduces `StarknetWrapper`, a wrapper class of
starkware.starknet.testing.starknet.Starknet.
"""

import json
import time
from copy import deepcopy
from typing import Dict
from web3 import Web3

import dill as pickle
from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
from starkware.starknet.business_logic.state.state import CarriedState, BlockInfo
from starkware.starknet.services.api.gateway.contract_address import calculate_contract_address
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Deploy
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.business_logic.transaction_fee import calculate_tx_fee_by_cairo_usage

from .origin import NullOrigin, Origin
from .general_config import DEFAULT_GENERAL_CONFIG
from .util import (
    Choice, StarknetDevnetException, TxStatus, DummyExecutionInfo,
    fixed_length_hex, enable_pickling, generate_state_update
)
from .contract_wrapper import ContractWrapper, call_internal_tx
from .transaction_wrapper import DeployTransactionWrapper, InvokeTransactionWrapper, TransactionWrapper
from .postman_wrapper import LocalPostmanWrapper
from .transactions import DevnetTransactions
from .contracts import DevnetContracts
from .blocks import DevnetBlocks

enable_pickling()

#pylint: disable=too-many-instance-attributes
class StarknetWrapper:
    """
    Wraps a Starknet instance and stores data to be returned by the server:
    contract states, transactions, blocks, storages.
    """

    def __init__(self):
        self.origin: Origin = NullOrigin()
        """Origin chain that this devnet was forked from."""

        self.transactions = DevnetTransactions(self.origin)

        self.contracts = DevnetContracts(self.origin)

        self.blocks = DevnetBlocks(self.origin)

        self.__starknet = None

        self.__postman_wrapper = None

        self.__l1_provider = None
        """Saves the L1 URL being used for L1 <> L2 communication."""

        self.lite_mode_block_hash = False

        self.lite_mode_deploy_hash = False

    @staticmethod
    def load(path: str) -> "StarknetWrapper":
        """Load a serialized instance of this class from `path`."""
        with open(path, "rb") as file:
            return pickle.load(file)

    async def __get_state_copy(self) -> CarriedState:
        state = await self.__get_state()

        copied_state = deepcopy(state.state)
        copied_state.shared_state = state.state.shared_state

        return copied_state

    async def get_starknet(self):
        """
        Returns the underlying Starknet instance, creating it first if necessary.
        """
        if not self.__starknet:
            self.__starknet = await Starknet.empty(general_config=DEFAULT_GENERAL_CONFIG)

        return self.__starknet

    async def __get_state(self):
        """
        Returns the StarknetState of the underlyling Starknet instance,
        creating the instance first if necessary.
        """
        starknet = await self.get_starknet()
        return starknet.state

    async def __update_state(self):
        if not self.lite_mode_block_hash:
            previous_state = await self.__get_state_copy()
            assert previous_state is not None
            current_carried_state = (await self.__get_state()).state

            current_carried_state.block_info = BlockInfo(
                block_number=current_carried_state.block_info.block_number,
                gas_price=current_carried_state.block_info.gas_price,
                block_timestamp=int(time.time()),
            )

            updated_shared_state = await current_carried_state.shared_state.apply_state_updates(
                ffc=current_carried_state.ffc,
                previous_carried_state=previous_state,
                current_carried_state=current_carried_state
            )
            self.__starknet.state.state.shared_state = updated_shared_state

            return generate_state_update(previous_state, current_carried_state)

    async def __get_state_root(self):
        state = await self.__get_state()
        return state.state.shared_state.contract_states.root

    async def deploy(self, deploy_transaction: Deploy):
        """
        Deploys the contract specified with `transaction`.
        Returns (contract_address, transaction_hash).
        """

        state = await self.__get_state()
        contract_definition = deploy_transaction.contract_definition
        if self.lite_mode_deploy_hash:
            tx_hash = self.transactions.get_count()
        else:
            tx_hash = deploy_transaction.calculate_hash(state.general_config)

        contract_address = calculate_contract_address(
            caller_address=0,
            constructor_calldata=deploy_transaction.constructor_calldata,
            salt=deploy_transaction.contract_address_salt,
            contract_definition=deploy_transaction.contract_definition
        )

        starknet = await self.get_starknet()

        if not self.contracts.is_deployed(contract_address):
            try:
                contract = await starknet.deploy(
                    contract_def=contract_definition,
                    constructor_calldata=deploy_transaction.constructor_calldata,
                    contract_address_salt=deploy_transaction.contract_address_salt
                )
                execution_info = contract.deploy_execution_info
                error_message = None
                status = TxStatus.ACCEPTED_ON_L2

                self.contracts.store(contract.contract_address, ContractWrapper(contract, contract_definition))
                state_update = await self.__update_state()
            except StarkException as err:
                error_message = err.message
                status = TxStatus.REJECTED
                execution_info = DummyExecutionInfo()

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
            adapted_result, execution_info = await contract_wrapper.call_or_invoke(
                Choice.INVOKE,
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

        adapted_result, _ = await contract_wrapper.call_or_invoke(
            Choice.CALL,
            entry_point_selector=transaction.entry_point_selector,
            calldata=transaction.calldata,
            signature=transaction.signature,
            caller_address=0,
            max_fee=transaction.max_fee
        )

        return { "result": adapted_result }

    async def __store_transaction(self, tx_wrapper: TransactionWrapper, state_update: Dict, error_message: str=None
    ):
        """
        Stores the provided data as a deploy transaction in `self.transactions`.
        Generates a new block
        """

        if tx_wrapper.transaction["status"] == TxStatus.REJECTED:
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
        """Creates a Postman Wrapper instance and loads an already deployed Messaging contract in the L1 network"""

        # If no L1 network ID provided, will use a local testnet instance
        if network_id is None or network_id == "local":
            try:
                starknet = await self.get_starknet()
                starknet.state.l2_to_l1_messages_log.clear()
                self.__postman_wrapper = LocalPostmanWrapper(network_url)
                self.__postman_wrapper.load_mock_messaging_contract_in_l1(starknet,contract_address)
            except Exception as error:
                message = f"""Exception when trying to load the Starknet Messaging contract in a local testnet instance.
Make sure you have a local testnet instance running at the provided network url, and that the Messaging Contract is deployed at the provided address
Exception:
{error}"""
                raise StarknetDevnetException(message=message) from error
        else:
            message = "L1 interaction is only usable with a local running local testnet instance."
            raise StarknetDevnetException(message=message)

        self.__l1_provider = network_url
        return {
            "l1_provider": network_url,
            "address": self.__postman_wrapper.mock_starknet_messaging_contract.address
        }

    async def postman_flush(self) -> dict:
        """Handles all pending L1 <> L2 messages and sends them to the other layer. """

        state = await self.__get_state()

        if self.__postman_wrapper is None:
            return {}

        postman = self.__postman_wrapper.postman

        l1_to_l2_messages = json.loads(Web3.toJSON(self.__postman_wrapper.l1_to_l2_message_filter.get_new_entries()))
        l2_to_l1_messages = state.l2_to_l1_messages_log[postman.n_consumed_l2_to_l1_messages :]

        await self.__postman_wrapper.flush()

        return self.parse_l1_l2_messages(l1_to_l2_messages, l2_to_l1_messages)

    def parse_l1_l2_messages(self, l1_raw_messages, l2_raw_messages) -> dict:
        """Converts some of the values in the dictionaries from integer to hex and keys to snake_case."""

        for message in l1_raw_messages:
            message["args"]["selector"] = hex(message["args"]["selector"])
            message["args"]["to_address"] = fixed_length_hex(message["args"].pop("toAddress")) # L2 addresses need the leading 0
            message["args"]["from_address"] = message["args"].pop("fromAddress")
            message["args"]["payload"] = [hex(val) for val in message["args"]["payload"]]

            # change case to snake_case
            message["transaction_hash"] = message.pop("transactionHash")
            message["block_hash"] = message.pop("blockHash")
            message["block_number"] = message.pop("blockNumber")
            message["transaction_index"] = message.pop("transactionIndex")
            message["log_index"] = message.pop("logIndex")

        l2_messages = []
        for message in l2_raw_messages:
            new_message = {
                "from_address": fixed_length_hex(message.from_address), # L2 addresses need the leading 0
                "payload": [hex(val) for val in message.payload],
                "to_address": hex(message.to_address)
            }
            l2_messages.append(new_message)

        return {
            "l1_provider": self.__l1_provider,
            "consumed_messages": {
                "from_l1": l1_raw_messages,
                "from_l2": l2_messages
            }
        }

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
