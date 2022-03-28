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

    def __set_starknet_wrapper(self, starknet_wrapper: StarknetWrapper):
        """Sets starknet wrapper and creates new instance of dumper"""
        self.starknet_wrapper = starknet_wrapper
        self.dumper = Dumper(starknet_wrapper)

    def reset(self):
        """Reset the starknet wrapper and dumper instances"""
        self.__set_starknet_wrapper(StarknetWrapper())

    def load(self, load_path: str):
        """Loads starknet wrapper from path"""
        self.__set_starknet_wrapper(StarknetWrapper.load(load_path))

state = State()
