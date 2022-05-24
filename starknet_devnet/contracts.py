"""
Class for storing and handling contracts
"""

from typing import Dict
from .origin import Origin
from .util import (
    StarknetDevnetException,
    fixed_length_hex
)
from .contract_wrapper import ContractWrapper

class DevnetContracts:
    """
    This class is used to store the deployed contracts of the devnet.
    """

    def __init__(self, origin: Origin):
        self.origin = origin
        self.__instances: Dict[int, ContractWrapper] = {}

    def store(self, address: int, contract: ContractWrapper) -> None:
        """
        Store the contract wrapper.
        """
        self.__instances[address] = contract

    def is_deployed(self, address: int) -> bool:
        """
        Check if the contract is deployed.
        """
        return address in self.__instances

    def get_by_address(self, address: int) -> ContractWrapper:
        """
        Get the contract wrapper by address.
        """
        if not self.is_deployed(address):
            message = f"No contract at the provided address ({fixed_length_hex(address)})."
            raise StarknetDevnetException(message=message)

        return self.__instances[address]

    def get_code(self, address: int) -> str:
        """
        Get the contract code by address.
        """
        if not self.is_deployed(address):
            return self.origin.get_code(address)

        return self.__instances[address].code

    def get_full_contract(self, address: int) -> ContractWrapper:
        """
        Get the contract wrapper by address.
        """
        contract = self.get_by_address(address)
        return contract.contract_definition
