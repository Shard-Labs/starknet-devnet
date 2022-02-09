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

    @abstractmethod
    def set_web3(self, network_url: str):
        """Sets a Web3 instance for the wrapper"""

    @abstractmethod
    def deploy_mock_starknet_messaging_contract(self, starknet):
        """Deploys the Mock Messaging contract in an L1 network"""

    @abstractmethod
    def get_mock_messaging_contract_in_l1(self, starknet, contract_address):
        """Retrieves the Mock Messaging contract deployed in an L1 network"""

    @abstractmethod
    def set_eth_account(self):
        """Sets an EthAccount instance for the wrapper"""

    async def flush(self):
        """Handles the L1 <> L2 message exchange"""
        await self.postman.flush()

class GanachePostmanWrapper(PostmanWrapper):
    """Wrapper of Postman usage on a local testnet instantiated using Ganache"""

    def __init__(self, network_url: str):
        super().__init__()
        self.set_web3(network_url)
        self.set_eth_account()

    def set_web3(self, network_url: str):
        request_kwargs = {"timeout": TIMEOUT_FOR_WEB3_REQUESTS}
        self.web3 = Web3(HTTPProvider(network_url, request_kwargs=request_kwargs))

    def set_eth_account(self):
        self.eth_account = EthAccount(self.web3,self.web3.eth.accounts[0])

    def deploy_mock_starknet_messaging_contract(self, starknet):
        self.mock_starknet_messaging_contract = self.eth_account.deploy(load_nearby_contract("MockStarknetMessaging"))
        self.postman = Postman(self.mock_starknet_messaging_contract,starknet)

    def get_mock_messaging_contract_in_l1(self, starknet, contract_address):
        address = Web3.toChecksumAddress(contract_address)
        contract_json = load_nearby_contract("MockStarknetMessaging")
        abi = contract_json["abi"]
        w3_contract = self.web3.eth.contract(abi=abi,address=address)
        self.mock_starknet_messaging_contract = EthContract(self.web3,address,w3_contract,abi,self.eth_account)
        self.postman = Postman(self.mock_starknet_messaging_contract,starknet)
