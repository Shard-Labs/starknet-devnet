"""
Test endpoints directly.
"""

from test.settings import GANACHE_URL
from test.test_endpoints import load_file_content
from test.util import call, deploy, invoke
from test.web3_util import web3_call, web3_invoke

import json
import subprocess
import pytest

from starknet_devnet.server import app

STARKNET_MESSAGING_PATH = "/build/contracts/MockStarknetMessaging.json"
L1L2EXAMPLE_ETH_PATH = "/build/contracts/L1L2Example.json"

ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/l1l2.cairo/l1l2.json"
ABI_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract_abi.json"

L1L2_EXAMPLE_CONTRACT_ADDRESS: str
MESSAGING_CONTRACT_ADDRESS: str
L2_CONTRACT_ADDRESS: str

@pytest.mark.web3_deploy
def test_init_ganache():
    """Initializes a new Ganache instance and a new Mock Messaging contract"""
    args = "ganache-cli -p 5005 --chainId 32 --networkId 32 --gasLimit 8000000 --allow-unlimited-contract-size &"
    subprocess.run(args, encoding="utf-8", check=False, capture_output=True)
    deploy_messaging_contract_request = {
        "networkUrl": GANACHE_URL
    }
    resp = app.test_client().post(
        "/postman/deploy_l1_messaging_contract",
        content_type="application/json",
        data=json.dumps(deploy_messaging_contract_request)
    )
    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert "address" in resp_dict
    assert resp_dict["l1_provider"] == GANACHE_URL
    print("here4")

@pytest.mark.web3_deploy
def test_deploy_l1_contracts():
    """Deploys Ethereum contracts in the Ganache instance, including the L1L2Example and MockStarknetMessaging contracts"""

    global MESSAGING_CONTRACT_ADDRESS # pylint: disable=global-statement
    global L1L2_EXAMPLE_CONTRACT_ADDRESS # pylint: disable=global-statement

    args = "( cd test && truffle migrate)"
    output = subprocess.run(args, encoding="utf-8", check=False, capture_output=True)
    assert output.returncode == 0

    messaging_contract = json.loads(load_file_content(STARKNET_MESSAGING_PATH))
    l1l2_example_contract = json.loads(load_file_content(L1L2EXAMPLE_ETH_PATH))

    MESSAGING_CONTRACT_ADDRESS = messaging_contract["networks"]["32"]["address"]
    L1L2_EXAMPLE_CONTRACT_ADDRESS = l1l2_example_contract["networks"]["32"]["address"]

@pytest.mark.deploy
def test_init_l2_contract():
    """Deploys the L1L2Example cairo contract"""

    global L2_CONTRACT_ADDRESS # pylint: disable=global-statement
    deploy_info = deploy(CONTRACT_PATH)
    # increase and withdraw balance
    invoke(
        function="increase_balance ",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["1","3333"]
    )
    invoke(
        function="withdraw",
        address=deploy_info["address"],
        abi_path=ABI_PATH,
        inputs=["1","1000"]
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

@pytest.mark.web3_deploy
def test_load_messaging_contract():
    """Loads a Mock Messaging contract already deployed in the Ganache instance"""

    load_messaging_contract_request = {
        "networkUrl": GANACHE_URL,
        "address": MESSAGING_CONTRACT_ADDRESS
    }

    resp = app.test_client().post(
        "/postman/deploy_l1_messaging_contract",
        content_type="application/json",
        data=json.dumps(load_messaging_contract_request)
    )

    resp_dict = json.loads(resp.data.decode("utf-8"))
    assert resp_dict["address"] == MESSAGING_CONTRACT_ADDRESS
    assert resp_dict["l1_provider"] == GANACHE_URL

@pytest.mark.web3_messaging
def test_l1_l2_message_exchange():
    """Tests message exchange"""

    # assert contract balance when starting
    balance = web3_call("userBalances",GANACHE_URL,["1"],L1L2_EXAMPLE_CONTRACT_ADDRESS,L1L2EXAMPLE_ETH_PATH)
    assert balance == 0

    # withdraw in l1 and assert contract balance
    web3_invoke("withdraw",GANACHE_URL,[L2_CONTRACT_ADDRESS,"1","1000"],L1L2_EXAMPLE_CONTRACT_ADDRESS,L1L2EXAMPLE_ETH_PATH)
    balance = web3_call("userBalances",GANACHE_URL,["1"],L1L2_EXAMPLE_CONTRACT_ADDRESS,L1L2EXAMPLE_ETH_PATH)
    assert balance == 1000

    # assert l2 contract balance
    l2_balance = call(
        function="get_balance",
        address=L1L2_EXAMPLE_CONTRACT_ADDRESS,
        abi_path=ABI_PATH,
        inputs=["1"]
    )
    assert l2_balance == 2333

    # deposit in l1 and assert contract balance
    web3_invoke("deposit",GANACHE_URL,[L2_CONTRACT_ADDRESS,"1","600"],L1L2_EXAMPLE_CONTRACT_ADDRESS,L1L2EXAMPLE_ETH_PATH)
    balance = web3_call("userBalances",GANACHE_URL,["1"],L1L2_EXAMPLE_CONTRACT_ADDRESS,L1L2EXAMPLE_ETH_PATH)
    assert balance == 400

    # flush postman messages
    app.test_client().post(
        "/postman/flush"
    )

    # assert l2 contract balance
    l2_balance = call(
        function="get_balance",
        address=L1L2_EXAMPLE_CONTRACT_ADDRESS,
        abi_path=ABI_PATH,
        inputs=["1"]
    )
    assert l2_balance == 2933
