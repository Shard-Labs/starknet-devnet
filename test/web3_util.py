"""Util functions for invoking and calling Web3 contracts"""

from solcx import compile_source
from web3 import Web3


def web3_compile(source):
    """Compiles a Solidity contract"""
    compiled_sol = compile_source(source,output_values=['abi', 'bin'])
    contract_id, contract_interface = compiled_sol.popitem() # pylint: disable=unused-variable
    return contract_interface

def web3_deploy(web3: Web3, contract_interface, *inputs):
    """Deploys a Solidity contract"""
    abi=contract_interface['abi']
    bytecode=contract_interface['bytecode']
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(*inputs).transact()
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

def web3_transact(function, contract,  *inputs):
    """Invokes a function in a Web3 contract"""

    #address=Web3.toChecksumAddress(contract_address)

    #abi=json.loads(load_file_content(abi_path))["abi"]
    #contract = web3.eth.contract(address=address,abi=abi)

    contract_function = contract.get_function_by_name(function)(*inputs)
    tx_hash = contract_function.transact()
    #tx_hash = contract_function.transact({"from": web3.eth.accounts[0], "value": 0})

    return tx_hash

def web3_call(function, contract, *inputs):
    """Invokes a function in a Web3 contract"""

    #address=Web3.toChecksumAddress(contract_address)

    #abi=json.loads(load_file_content(abi_path))["abi"]
    #contract = web3.eth.contract(address=address,abi=abi)

    value = contract.get_function_by_name(function)(*inputs).call()

    return value
