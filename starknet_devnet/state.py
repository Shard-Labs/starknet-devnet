"""
Global state singletone
"""

from .starknet_wrapper import StarknetWrapper
from .dump import Dumper

class State():
    """
    Stores starknet wrapper and dumper
    """
    def __init__(self):
        self.starknet_wrapper = StarknetWrapper()
        self.dumper = Dumper(self.starknet_wrapper)

    def reset(self):
        """Reset the starknet wrapper and dumper instances"""
        self.starknet_wrapper = StarknetWrapper()
        self.dumper = Dumper(self.starknet_wrapper)

state = State()
