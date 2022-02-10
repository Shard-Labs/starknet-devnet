import json
from web3 import Web3

from test.test_endpoints import load_file_content

def web3_invoke(function, url, inputs, contract_address, abi_path):
    """Invokes a function in a Web3 contract"""

    web3 = Web3(Web3.HTTPProvider(url))
    address=Web3.toChecksumAddress(contract_address)

    abi=json.loads(load_file_content(abi_path))
    contract = web3.eth.contract(address=address,abi=abi)

    contract_function = contract.functions.__getattr__(function)(inputs)
    tx_hash = contract_function.transact({"from": web3.eth.accounts[0], "value": 0})

    return tx_hash

def web3_call(function, url, inputs, contract_address, abi_path):
    """Invokes a function in a Web3 contract"""

    web3 = Web3(Web3.HTTPProvider(url))
    address=Web3.toChecksumAddress(contract_address)

    abi=json.loads(load_file_content(abi_path))
    contract = web3.eth.contract(address=address,abi=abi)

    value = contract.call().__getattr__(function)(inputs)

    return value