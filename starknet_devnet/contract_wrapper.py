from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.testing.contract import StarknetContract

class ContractWrapper:
    def __init__(self, contract: StarknetContract, contract_definition: ContractDefinition):
        self.contract: StarknetContract = contract
        self.code: dict = {
            "abi": contract_definition.abi,
            "bytecode": [hex(el) for el in contract_definition.program.data]
        }

        self.types: dict = self.extract_types(contract_definition.abi)

    def extract_types(self, abi):
        """
        Extracts the types (structs) used in the contract whose ABI is provided.
        """

        structs = [entry for entry in abi if entry["type"] == "struct"]
        type_dict = { struct["name"]: struct for struct in structs }
        return type_dict
