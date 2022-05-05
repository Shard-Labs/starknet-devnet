"""
Block manager
"""

import time

from starkware.starknet.business_logic.state.state import BlockInfo

from .general_config import DEFAULT_GENERAL_CONFIG

class BlockInfoManager():
    """
    class
    """
    block_timestamp_offset: int = 0

    def __init__(self, start_block_number: int, gas_price: int, start_time_ns: int):
        self.block_number = start_block_number or 0
        self.gas_price = gas_price or DEFAULT_GENERAL_CONFIG.min_gas_price

        if start_time_ns is not None:
            self.block_timestamp_offset = start_time_ns - time.time_ns()

    def generate_block_info(self):
        """
        generate block info
        """
        self.block_number += 1

        return BlockInfo(
            gas_price=self.gas_price,
            block_number=self.block_number,
            block_timestamp=time.time_ns() + self.block_timestamp_offset
        )

    def increase_time(self, time_ns: int):
        """
        Increases block timestamp offeset
        """
        self.block_timestamp_offset += time_ns

    def set_time(self, time_ns: int):
        """
        Resets the block timestamp offset
        """
        self.block_timestamp_offset = time_ns - time.time_ns()
