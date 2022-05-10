"""
Block info generator for the Starknet Devnet.
"""

import time

from starkware.starknet.business_logic.state.state import BlockInfo

def now() -> int:
    """Get the current time in seconds."""
    return int(time.time())

class BlockInfoGenerator():
    """Generator of BlockInfo objects with the correct timestamp"""

    def __init__(self, start_time: int = None):
        self.block_timestamp_offset = 0
        self.next_block_start_time = start_time

    def next_block(self, block_info: BlockInfo):
        """
        Returns the next block info with the correct timestamp
        """
        if self.next_block_start_time is None:
            block_timestamp = now() + self.block_timestamp_offset
        else:
            block_timestamp = self.next_block_start_time
            self.block_timestamp_offset = block_timestamp - now()
            self.next_block_start_time = None

        return BlockInfo(
            gas_price=block_info.gas_price,
            block_number=block_info.block_number,
            block_timestamp=block_timestamp
        )

    def increase_time(self, time: int):
        """
        Increases block timestamp offeset
        """
        self.block_timestamp_offset += time

    def set_next_block_time(self, time: int):
        """
        Sets the timestamp of next block
        """
        self.next_block_start_time = time
