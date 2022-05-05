"""
Contains code for wrapping StarknetContract instances.
"""

from dataclasses import dataclass
from typing import List

from starkware.starknet.services.api.contract_definition import ContractDefinition, EntryPointType
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.utils.api_utils import cast_to_felts
from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
from starkware.starknet.definitions import constants
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.business_logic.execution.execute_entry_point import ExecuteEntryPoint
from starkware.starknet.business_logic.execution.objects import (
    TransactionExecutionContext,
    TransactionExecutionInfo,
)
from starkware.starknet.testing.state import StarknetState

from starknet_devnet.util import Choice

async def call_internal_tx(starknet_state: StarknetState, internal_tx: InternalInvokeFunction):
    """
    Executes an internal transaction.
    """
    with starknet_state.state.copy_and_apply() as state_copy:
        tx_execution_context = TransactionExecutionContext.create(
            account_contract_address=internal_tx.contract_address,
            transaction_hash=internal_tx.hash_value,
            signature=internal_tx.signature,
            max_fee=internal_tx.max_fee,
            n_steps=starknet_state.general_config.invoke_tx_max_n_steps,
            version=internal_tx.version,
        )
        call = ExecuteEntryPoint(
            contract_address=internal_tx.contract_address,
            code_address=internal_tx.code_address,
            entry_point_selector=internal_tx.entry_point_selector,
            entry_point_type=internal_tx.entry_point_type,
            calldata=internal_tx.calldata,
            caller_address=internal_tx.caller_address,
        )
        call_info = await call.execute(
            state=state_copy,
            general_config=starknet_state.general_config,
            tx_execution_context=tx_execution_context
        )
        fee_transfer_info = None
        actual_fee = 0

    return TransactionExecutionInfo(
        call_info=call_info, fee_transfer_info=fee_transfer_info, actual_fee=actual_fee
    )

@dataclass
class ContractWrapper:
    """
    Wraps a StarknetContract, storing its types and code for later use.
    """
    def __init__(self, contract: StarknetContract, contract_definition: ContractDefinition):
        self.contract: StarknetContract = contract
        self.contract_definition = contract_definition.remove_debug_info().dump()

        self.code: dict = {
            "abi": contract_definition.abi,
            "bytecode": self.contract_definition["program"]["data"]
        }


    # pylint: disable=too-many-arguments
    async def call_or_invoke(
        self,
        choice: Choice,
        entry_point_selector: int,
        calldata: List[int],
        signature: List[int],
        caller_address: int,
        max_fee: int
    ):
        """
        Depending on `choice`, performs the call or invoke of the function
        identified with `entry_point_selector`, potentially passing in `calldata` and `signature`.
        """
        if choice == Choice.CALL:
            execution_info = await self.call(entry_point_selector, calldata, signature, caller_address, max_fee)
        else:
            execution_info = await self.invoke(entry_point_selector, calldata, signature, caller_address, max_fee)

        result = list(map(hex, execution_info.call_info.retdata))
        return result, execution_info

    async def call(
        self,
        entry_point_selector: int,
        calldata: List[int],
        signature: List[int],
        caller_address: int,
        max_fee: int
    ):
        """
        Calls the function identified with `entry_point_selector`, potentially passing in `calldata` and `signature`.
        """
        starknet_state = self.contract.state.copy()
        contract_address = self.contract.contract_address
        selector = entry_point_selector

        if isinstance(contract_address, str):
            contract_address = int(contract_address, 16)
        assert isinstance(contract_address, int)

        if isinstance(selector, str):
            selector = get_selector_from_name(selector)
        assert isinstance(selector, int)

        if signature is None:
            signature = []

        internal_tx = InternalInvokeFunction.create(
            contract_address=contract_address,
            entry_point_selector=selector,
            entry_point_type=EntryPointType.EXTERNAL,
            calldata=calldata,
            max_fee=max_fee,
            signature=signature,
            caller_address=caller_address,
            nonce=None,
            chain_id=starknet_state.general_config.chain_id.value,
            version=constants.QUERY_VERSION,
            only_query=True,
        )

        return await call_internal_tx(starknet_state, internal_tx)

    async def invoke(
        self,
        entry_point_selector: int,
        calldata: List[int],
        signature: List[int],
        caller_address: int,
        max_fee: int
    ):
        """
        Invokes the function identified with `entry_point_selector`, potentially passing in `calldata` and `signature`.
        """

        return await self.contract.state.invoke_raw(
            contract_address=self.contract.contract_address,
            selector=entry_point_selector,
            calldata=calldata,
            caller_address=caller_address,
            max_fee=max_fee,
            signature=signature and cast_to_felts(values=signature),
        )
