"""
Class for storing and handling transactions.
"""

from .origin import Origin
from .transaction_wrapper import TransactionWrapper
from .constants import FAILURE_REASON_KEY


class DevnetTransactions:
    """
    This class is used to store transactions.
    """

    def __init__(self, origin: Origin):
        self.origin = origin
        self.__instances = {}

    def __get_transaction_by_hash(self, tx_hash: str) -> TransactionWrapper or None:
        """
        Get a transaction by hash.
        """
        numeric_hash = int(tx_hash, 16)
        return self.__instances.get(numeric_hash)

    def get_count(self):
        """
        Get the number of transactions.
        """
        return len(self.__instances)

    def store(self, transaction: TransactionWrapper):
        """
        Store a transaction.
        """
        numeric_hash = int(transaction.transaction_hash, 16)
        self.__instances[numeric_hash] = transaction

    def get_transaction(self, tx_hash: str):
        """
        Get a transaction.
        """
        transaction = self.__get_transaction_by_hash(tx_hash)

        if transaction is None:
            return self.origin.get_transaction(tx_hash)

        return transaction.transaction

    def get_transaction_trace(self, tx_hash: str):
        """
        Get a transaction trace.
        """
        transaction = self.__get_transaction_by_hash(tx_hash)

        if transaction is None:
            return self.origin.get_transaction_trace(tx_hash)

        return transaction.trace

    def get_transaction_receipt(self, tx_hash: str):
        """
        Get a transaction receipt.
        """
        transaction = self.__get_transaction_by_hash(tx_hash)

        if transaction is None:
            return self.origin.get_transaction_receipt(tx_hash)

        return transaction.receipt

    def get_transaction_status(self, tx_hash: str):
        """
        Get a transaction status.
        """
        transaction_wrapper = self.__get_transaction_by_hash(tx_hash)

        if transaction_wrapper is None:
            return self.origin.get_transaction_status(tx_hash)

        transaction = transaction_wrapper.transaction

        # the transaction status object only needs 1-3 elements from the transaction_wrapper object
        status_response = {
            # "tx_status" always exists
            "tx_status": transaction["status"]
        }

        # "block_hash" will only exist after transaction enters ACCEPTED_ON_L2
        if "block_hash" in transaction:
            status_response["block_hash"] = transaction["block_hash"]

        # "tx_failure_reason" will only exist if the transaction was rejected.
        # the key in the transaction_wrapper object is "transaction_failure_reason"
        # first it must be checked if the object contains an element with that key
        if FAILURE_REASON_KEY in transaction:
            status_response["tx_failure_reason"] = transaction[FAILURE_REASON_KEY]

        return status_response
