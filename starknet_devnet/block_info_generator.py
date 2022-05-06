"""
Block info generator for the Starknet Devnet.
"""

import time

from starkware.starknet.business_logic.state.state import BlockInfo

class BlockInfoGenerator():
    """Generator of BlockInfo objects with the correct timestamp"""

    def __init__(self, start_time_ns: int = None):
        self.block_timestamp_offset = 0
        self.next_block_start_time_ns = start_time_ns if start_time_ns else None

    def next_block(self, block_info: BlockInfo):
        """
        Returns the next block info with the correct timestamp
        """
        if self.next_block_start_time_ns is None:
            block_timestamp = time.time_ns() + self.block_timestamp_offset
        else:
            block_timestamp = self.next_block_start_time_ns
            self.block_timestamp_offset = block_timestamp - time.time_ns()
            self.next_block_start_time_ns = None

        return BlockInfo(
            gas_price=block_info.gas_price,
            block_number=block_info.block_number,
            block_timestamp=block_timestamp
        )

    def increase_time(self, time_ns: int):
        """
        Increases block timestamp offeset
        """
        self.block_timestamp_offset += time_ns

    def set_next_block_time(self, time_ns: int):
        """
        Sets the timestamp of next block
        """
        self.next_block_start_time_ns = time_ns
