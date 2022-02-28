"""
This module wraps the usage of Postman for L1 <> L2 interaction.
"""
from abc import ABC, abstractmethod
from web3 import HTTPProvider, Web3
from starkware.contracts.utils import load_nearby_contract

from .postman.postman import Postman
from .postman.eth_test_utils import EthAccount, EthContract

from .constants import TIMEOUT_FOR_WEB3_REQUESTS


class PostmanWrapper(ABC):
    """Postman Wrapper base class"""

    @abstractmethod
    def __init__(self):
        self.postman: Postman = None
        self.web3: Web3 = None
        self.mock_starknet_messaging_contract: EthContract = None
        self.eth_account: EthAccount = None
        self.l1_to_l2_message_filter = None

    @abstractmethod
    def load_mock_messaging_contract_in_l1(self, starknet, contract_address):
        """Retrieves the Mock Messaging contract deployed in an L1 network"""

    async def flush(self):
        """Handles the L1 <> L2 message exchange"""
        await self.postman.flush()

class LocalPostmanWrapper(PostmanWrapper):
    """Wrapper of Postman usage on a local testnet instantiated using a local testnet"""

    def __init__(self, network_url: str):
        super().__init__()
        request_kwargs = {"timeout": TIMEOUT_FOR_WEB3_REQUESTS}
        self.web3 = Web3(HTTPProvider(network_url, request_kwargs=request_kwargs))
        self.eth_account = EthAccount(self.web3,self.web3.eth.accounts[0])

    def load_mock_messaging_contract_in_l1(self, starknet, contract_address):
        if contract_address is None:
            self.mock_starknet_messaging_contract = self.eth_account.deploy(load_nearby_contract("MockStarknetMessaging"))
        else:
            address = Web3.toChecksumAddress(contract_address)
            contract_json = load_nearby_contract("MockStarknetMessaging")
            abi = contract_json["abi"]
            w3_contract = self.web3.eth.contract(abi=abi,address=address)
            self.mock_starknet_messaging_contract = EthContract(self.web3,address,w3_contract,abi,self.eth_account)

        self.postman = Postman(self.mock_starknet_messaging_contract,starknet)
        self.l1_to_l2_message_filter = self.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(fromBlock="latest")
