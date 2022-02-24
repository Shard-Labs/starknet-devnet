"""
Test endpoints directly.
"""



from test.settings import L1_URL, GATEWAY_URL
from test.util import call, deploy, invoke, run_devnet_in_background, load_file_content
from test.web3_util import web3_call, web3_compile, web3_deploy, web3_transact

import atexit
import time
import json
import subprocess
import requests
import pytest

from solcx import install_solc
from web3 import Web3
from web3.contract import Contract





ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/l1l2.cairo/l1l2.json"
ABI_PATH = f"{ARTIFACTS_PATH}/l1l2.cairo/l1l2_abi.json"
STARKNET_MESSAGING_PATH = f"{ARTIFACTS_PATH}/MockStarknetMessaging.sol"
L1L2_EXAMPLE_ETH_PATH = f"{ARTIFACTS_PATH}/L1L2Example.sol"

L1L2_EXAMPLE_CONTRACT_DEFINITION: Contract
MESSAGING_CONTRACT_DEFINITION: Contract
L2_CONTRACT_ADDRESS: str

WEB3: Web3

@pytest.mark.web3_deploy
def test_init_local_testnet():
    """Initializes a new local Hardhat testnet instance and a new Mock Messaging contract"""

    global WEB3 # pylint: disable=global-statement

    # Setup L1 testnet
    command = ["npx", "hardhat", "node"]
    # pylint: disable=consider-using-with
    proc = subprocess.Popen(command,cwd="starknet-hardhat-example", close_fds=True, stdout=subprocess.PIPE)
    time.sleep(30)
    atexit.register(proc.kill)
    WEB3 = Web3(Web3.HTTPProvider(L1_URL))
    WEB3.eth.default_account = WEB3.eth.accounts[0]
    run_devnet_in_background(sleep_seconds=1)
    deploy_messaging_contract_request = {
        "networkUrl": L1_URL
    }
    resp = requests.post(
        f"{GATEWAY_URL}/postman/load_l1_messaging_contract",
        json=deploy_messaging_contract_request
    )
    resp_dict = json.loads(resp.text)
    assert "address" in resp_dict
    assert resp_dict["l1_provider"] == L1_URL

@pytest.mark.web3_deploy
def test_deploy_l1_contracts():
    """Deploys Ethereum contracts in the Hardhat testnet instance, including the L1L2Example and MockStarknetMessaging contracts"""

    global MESSAGING_CONTRACT_DEFINITION # pylint: disable=global-statement
    global L1L2_EXAMPLE_CONTRACT_DEFINITION # pylint: disable=global-statement
    global WEB3 # pylint: disable=global-statement disable=global-variable-not-assigned

    install_solc(version='latest')
    messaging_contract = load_file_content(STARKNET_MESSAGING_PATH)
    l1l2_example_contract = load_file_content(L1L2_EXAMPLE_ETH_PATH)

    messaging_contract_interface = web3_compile(messaging_contract)
    l1l2_example_contract_interface = web3_compile(l1l2_example_contract)

    MESSAGING_CONTRACT_DEFINITION = web3_deploy(WEB3,messaging_contract_interface)
    L1L2_EXAMPLE_CONTRACT_DEFINITION = web3_deploy(WEB3,l1l2_example_contract_interface,MESSAGING_CONTRACT_DEFINITION.address)

@pytest.mark.web3_deploy
def test_load_messaging_contract():
    """Loads a Mock Messaging contract already deployed in the Ganache instance"""

    load_messaging_contract_request = {
        "networkUrl": L1_URL,
        "address": MESSAGING_CONTRACT_DEFINITION.address
    }

    resp = requests.post(
        f"{GATEWAY_URL}/postman/load_l1_messaging_contract",
        json=load_messaging_contract_request
    )

    resp_dict = json.loads(resp.text)
    assert resp_dict["address"] == MESSAGING_CONTRACT_DEFINITION.address
    assert resp_dict["l1_provider"] == L1_URL

@pytest.mark.deploy
def test_init_l2_contract():
    """Deploys the L1L2Example cairo contract"""

    global L2_CONTRACT_ADDRESS # pylint: disable=global-statement
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
        inputs=["1","1000",L1L2_EXAMPLE_CONTRACT_DEFINITION.address]
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

    L2_CONTRACT_ADDRESS=deploy_info["address"]
    assert value == "2333"

@pytest.mark.web3_messaging
def test_l1_l2_message_exchange():
    """Tests message exchange"""

    # assert contract balance when starting
    balance = web3_call(
        "userBalances",
        L1L2_EXAMPLE_CONTRACT_DEFINITION,
        1)
    assert balance == 0

    # withdraw in l1 and assert contract balance
    web3_transact(
        "withdraw",
        L1L2_EXAMPLE_CONTRACT_DEFINITION,
        int(L2_CONTRACT_ADDRESS,base=16), 1, 1000)

    balance = web3_call(
        "userBalances",
        L1L2_EXAMPLE_CONTRACT_DEFINITION,
        1)
    assert balance == 1000

    # assert l2 contract balance
    l2_balance = call(
        function="get_balance",
        address=L2_CONTRACT_ADDRESS,
        abi_path=ABI_PATH,
        inputs=["1"]
    )

    assert l2_balance == "2333"

    # deposit in l1 and assert contract balance
    web3_transact(
        "deposit",
        L1L2_EXAMPLE_CONTRACT_DEFINITION,
        int(L2_CONTRACT_ADDRESS,base=16), 1, 600)

    balance = web3_call(
        "userBalances",
        L1L2_EXAMPLE_CONTRACT_DEFINITION,
        1)

    assert balance == 400

    # flush postman messages
    requests.post(
        f"{GATEWAY_URL}/postman/flush"
    )

    # assert l2 contract balance
    l2_balance = call(
        function="get_balance",
        address=L2_CONTRACT_ADDRESS,
        abi_path=ABI_PATH,
        inputs=["1"]
    )

    assert l2_balance == "2933"
