"""Util functions for invoking and calling Web3 contracts"""

from test.test_endpoints import load_file_content

import json
from web3 import Web3


def web3_transact(function, url, contract_address, abi_path, *inputs):
    """Invokes a function in a Web3 contract"""

    web3 = Web3(Web3.HTTPProvider(url))
    address=Web3.toChecksumAddress(contract_address)

    abi=json.loads(load_file_content(abi_path))["abi"]
    contract = web3.eth.contract(address=address,abi=abi)

    contract_function = contract.get_function_by_name(function)(*inputs)
    tx_hash = contract_function.transact({"from": web3.eth.accounts[0], "value": 0})

    return tx_hash

def web3_call(function, url, contract_address, abi_path, *inputs):
    """Invokes a function in a Web3 contract"""

    web3 = Web3(Web3.HTTPProvider(url))
    address=Web3.toChecksumAddress(contract_address)

    abi=json.loads(load_file_content(abi_path))["abi"]
    contract = web3.eth.contract(address=address,abi=abi)

    value = contract.get_function_by_name(function)(*inputs).call()

    return value
