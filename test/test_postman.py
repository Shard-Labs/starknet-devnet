"""
Test postman usage. This test has one single pytest case, because the whole flow needs to be tested, and requires all steps to be performed
"""



from test.settings import L1_URL, GATEWAY_URL
from test.util import call, deploy, invoke, run_devnet_in_background, load_file_content
from test.web3_util import web3_call, web3_deploy, web3_transact

import time
import json
import subprocess
import requests
import pytest

from web3 import Web3

from .shared import ARTIFACTS_PATH

CONTRACT_PATH = f"{ARTIFACTS_PATH}/l1l2.cairo/l1l2.json"
ABI_PATH = f"{ARTIFACTS_PATH}/l1l2.cairo/l1l2_abi.json"

ETH_CONTRACTS_PATH = "../starknet-hardhat-example/artifacts/contracts"
STARKNET_MESSAGING_PATH = f"{ETH_CONTRACTS_PATH}/MockStarknetMessaging.sol/MockStarknetMessaging.json"
L1L2_EXAMPLE_PATH = f"{ETH_CONTRACTS_PATH}/L1L2.sol/L1L2Example.json"

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # Setup devnet
    devnet_proc = run_devnet_in_background(sleep_seconds=5)
    # Setup L1 testnet
    command = ["npx", "hardhat", "node"]
    # pylint: disable=consider-using-with
    l1_proc = subprocess.Popen(command,cwd="starknet-hardhat-example", close_fds=True, stdout=subprocess.PIPE)
    time.sleep(25)
    yield

    # after test
    devnet_proc.kill()
    l1_proc.kill()

def init_messaging_contract():
    """Initializes the messaging contract"""

    deploy_messaging_contract_request = {
        "networkUrl": L1_URL
    }
    resp = requests.post(
        f"{GATEWAY_URL}/postman/load_l1_messaging_contract",
        json=deploy_messaging_contract_request
    )
    return json.loads(resp.text)


def deploy_l1_contracts(web3):
    """Deploys Ethereum contracts in the Hardhat testnet instance, including the L1L2Example and MockStarknetMessaging contracts"""

    messaging_contract = json.loads(load_file_content(STARKNET_MESSAGING_PATH))
    l1l2_example_contract = json.loads(load_file_content(L1L2_EXAMPLE_PATH))

    starknet_messaging_contract = web3_deploy(web3,messaging_contract)
    l1l2_example = web3_deploy(web3,l1l2_example_contract,starknet_messaging_contract.address)

    return starknet_messaging_contract, l1l2_example


def load_messaging_contract(starknet_messaging_contract_address):
    """Loads a Mock Messaging contract already deployed in the local testnet instance"""

    load_messaging_contract_request = {
        "networkUrl": L1_URL,
        "address": starknet_messaging_contract_address
    }

    resp = requests.post(
        f"{GATEWAY_URL}/postman/load_l1_messaging_contract",
        json=load_messaging_contract_request
    )

    return json.loads(resp.text)

def init_l2_contract(l1l2_example_contract_address):
    """Deploys the L1L2Example cairo contract, returns the result of calling 'get_balance' """

    deploy_info = deploy(CONTRACT_PATH)

    # increase and withdraw balance
    invoke(
        function="increase_balance",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["1","3333"]
    )
    invoke(
        function="withdraw",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["1","1000",l1l2_example_contract_address]
    )

    # flush postman messages
    requests.post(
        f"{GATEWAY_URL}/postman/flush"
    )

    #assert balance
    value = call(
        function="get_balance",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["1"]
    )

    assert value == "2333"
    return deploy_info["address"]

def l1_l2_message_exchange(web3, l1l2_example_contract, l2_contract_address):
    """Tests message exchange"""

    # assert contract balance when starting
    balance = web3_call(
        "userBalances",
        l1l2_example_contract,
        1)
    assert balance == 0

    # withdraw in l1 and assert contract balance
    web3_transact(
        web3,
        "withdraw",
        l1l2_example_contract,
        int(l2_contract_address,base=16), 1, 1000)

    balance = web3_call(
        "userBalances",
        l1l2_example_contract,
        1)
    assert balance == 1000

    # assert l2 contract balance
    l2_balance = call(
        function="get_balance",
        address=l2_contract_address,
        abi_path=ABI_PATH,
        inputs=["1"]
    )

    assert l2_balance == "2333"

    # deposit in l1 and assert contract balance
    web3_transact(
        web3,
        "deposit",
        l1l2_example_contract,
        int(l2_contract_address,base=16), 1, 600)

    balance = web3_call(
        "userBalances",
        l1l2_example_contract,
        1)

    assert balance == 400

    # flush postman messages
    requests.post(
        f"{GATEWAY_URL}/postman/flush"
    )

    # assert l2 contract balance
    l2_balance = call(
        function="get_balance",
        address=l2_contract_address,
        abi_path=ABI_PATH,
        inputs=["1"]
    )

    assert l2_balance == "2933"

@pytest.mark.web3_messaging
def test_postman():
    """Test postman with a complete L1<>L2 flow"""
    l1l2_example_contract = None
    starknet_messaging_contract = None
    l2_contract_address = None
    web3 = None

    # Test initializing a local L1 network
    init_resp = init_messaging_contract()
    web3 = Web3(Web3.HTTPProvider(L1_URL))
    web3.eth.default_account = web3.eth.accounts[0]
    assert "address" in init_resp
    assert init_resp["l1_provider"] == L1_URL

    starknet_messaging_contract, l1l2_example_contract = deploy_l1_contracts(web3)

    # Test loading the messaging contract
    load_resp = load_messaging_contract(starknet_messaging_contract.address)
    assert load_resp["address"] == starknet_messaging_contract.address
    assert load_resp["l1_provider"] == L1_URL

    # Test initializing the l2 example contract
    l2_contract_address = init_l2_contract(l1l2_example_contract.address)

    l1_l2_message_exchange(web3,l1l2_example_contract,l2_contract_address)
