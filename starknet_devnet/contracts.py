"""
Class for storing and handling contracts
"""

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
        self.__intstances = {}

    def store(self, address: str, contract: ContractWrapper) -> None:
        """
        Store the contract wrapper.
        """
        self.__intstances[address] = contract

    def is_deployed(self, address: str) -> bool:
        """
        Check if the contract is deployed.
        """
        return address in self.__intstances

    def get_by_address(self, address: str) -> ContractWrapper:
        """
        Get the contract wrapper by address.
        """
        if not self.is_deployed(address):
            message = f"No contract at the provided address ({fixed_length_hex(address)})."
            raise StarknetDevnetException(message=message)

        return self.__intstances[address]

    def get_code(self, address: str) -> str:
        """
        Get the contract code by address.
        """
        if not self.is_deployed(address):
            return self.origin.get_code(address)

        return self.__intstances[address].code

    def get_full_contract(self, address: str) -> ContractWrapper:
        """
        Get the contract wrapper by address.
        """
        contract = self.get_by_address(address)
        return contract.contract_definition
