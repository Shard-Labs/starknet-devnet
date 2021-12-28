"""
Contains code for wrapping transactions.
"""

from dataclasses import dataclass

@dataclass
class TransactionWrapper:
    """Wraps a transaction and its receipt."""
    def __init__(self, transaction, receipt):
        self.transaction = transaction
        self.receipt = receipt
