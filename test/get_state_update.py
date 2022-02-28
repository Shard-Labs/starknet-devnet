import requests

from .settings import FEEDER_GATEWAY_URL
from .util import run_devnet_in_background, deploy, get_block

ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract.json"
ABI_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract_abi.json"

def get_state_update():
    """Get state update"""
    res =  requests.get(f"{FEEDER_GATEWAY_URL}/feeder_gateway/get_state_update")

    return res.json()

def deploy_empty_contract():
    """
    Deploy sample contract with balance = 0.
    Returns contract address.
    """
    deploy_dict = deploy(CONTRACT_PATH, inputs=["0"])
    contract_address = deploy_dict["address"]

    return contract_address

def main():
    """Main the man"""
    devnet_proc = run_devnet_in_background()

    print(get_state_update())

    deploy_empty_contract()

    print(get_state_update())

    print(get_block())

    devnet_proc.kill()

if __name__=="__main__":
    main()
