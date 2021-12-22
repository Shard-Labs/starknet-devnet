"""
Contains classes that provide the abstraction of L2 blockchain.
"""

from starknet_devnet.util import TxStatus


class Origin:
    """
    Abstraction of an L2 blockchain.
    """

    def get_transaction_status(self, transaction_hash: str):
        """Returns the status of the transaction."""
        raise NotImplementedError

    def get_transaction(self, transaction_hash: str):
        """Returns the transaction object."""
        raise NotImplementedError

    def get_block(self, block_hash: str, block_number: int):
        """Returns the block identified with either its hash or its number."""
        raise NotImplementedError

    def get_code(self, contract_address: int) -> dict:
        """Returns the code of the contract."""
        raise NotImplementedError

    def get_storage_at(self, contract_address: int, key: int) -> str:
        """Returns the storage identified with `key` at `contract_address`."""
        raise NotImplementedError


class NullOrigin(Origin):
    """
    A default class to comply with the Origin interface.
    """

    def get_transaction_status(self, transaction_hash: str):
        return {
            "tx_status": TxStatus.NOT_RECEIVED.name
        }

    def get_transaction(self, transaction_hash: str):
        return {
            "status": TxStatus.NOT_RECEIVED.name,
            "transaction_hash": transaction_hash
        }

    def get_block(self, block_hash: str, block_number: int):
        raise NotImplementedError

    def get_code(self, contract_address: int):
        return {
            "abi": {},
            "bytecode": []
        }

    def get_storage_at(self, contract_address: int, key: int) -> str:
        return hex(0)
