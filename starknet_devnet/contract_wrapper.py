"""
Contains code for wrapping StarknetContract instances.
"""

from dataclasses import dataclass
from typing import List

from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo

from starknet_devnet.adapt import adapt_calldata, adapt_output
from starknet_devnet.util import Choice, StarknetDevnetException

def extract_types(abi):
    """
    Extracts the types (structs) used in the contract whose ABI is provided.
    """

    structs = [entry for entry in abi if entry["type"] == "struct"]
    type_dict = { struct["name"]: struct for struct in structs }
    return type_dict

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

        self.types: dict = extract_types(contract_definition.abi)

    async def call_or_invoke(self, choice: Choice, entry_point_selector: int, calldata: List[int], signature: List[int]):
        """
        Depending on `choice`, performs the call or invoke of the function
        identified with `entry_point_selector`, potentially passing in `calldata` and `signature`.
        """
        function_mapping = self.contract._abi_function_mapping # pylint: disable=protected-access
        for method_name in function_mapping:
            selector = get_selector_from_name(method_name)
            if selector == entry_point_selector:
                try:
                    method = getattr(self.contract, method_name)
                except NotImplementedError as nie:
                    raise StarknetDevnetException from nie
                function_abi = function_mapping[method_name]
                break
        else:
            raise StarknetDevnetException(message=f"Illegal method selector: {entry_point_selector}.")

        adapted_calldata = adapt_calldata(calldata, function_abi["inputs"], self.types)

        prepared = method(*adapted_calldata)
        called = getattr(prepared, choice.value)
        execution_info: StarknetTransactionExecutionInfo = await called(signature=signature)
        return adapt_output(execution_info.result), execution_info
