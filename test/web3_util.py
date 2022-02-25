"""Util functions for invoking and calling Web3 contracts"""

from solcx import compile_source
from web3 import Web3


def web3_compile(source, path):
    """Compiles a Solidity contract"""
    compiled_sol = compile_source(source,output_values=['abi', 'bin'],base_path=path)
    contract_interface = list(compiled_sol.values())[0]
    return contract_interface

def web3_deploy(web3: Web3, contract_interface, *inputs):
    """Deploys a Solidity contract"""
    abi=contract_interface['abi']
    bytecode=contract_interface['bin']
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(*inputs).transact()
    tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
    return web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

def web3_transact(web3: Web3, function, contract,  *inputs):
    """Invokes a function in a Web3 contract"""

    contract_function = contract.get_function_by_name(function)(*inputs)
    tx_hash = contract_function.transact()
    web3.eth.waitForTransactionReceipt(tx_hash)

    return tx_hash

def web3_call(function, contract, *inputs):
    """Invokes a function in a Web3 contract"""

    value = contract.get_function_by_name(function)(*inputs).call()

    return value
