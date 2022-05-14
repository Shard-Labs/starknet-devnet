"""
Block info generator for the Starknet Devnet.
"""

import time

from starkware.starknet.business_logic.state.state import BlockInfo
from starkware.starknet.definitions.general_config import StarknetGeneralConfig

def now() -> int:
    """Get the current time in seconds."""
    return int(time.time())

class BlockInfoGenerator():
    """Generator of BlockInfo objects with the correct timestamp"""

    def __init__(self, start_time: int = None):
        self.block_timestamp_offset = 0
        self.next_block_start_time = start_time

    def next_block(self, block_info: BlockInfo, general_config: StarknetGeneralConfig):
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
            block_timestamp=block_timestamp,
            sequencer_address=general_config.sequencer_address
        )

    def increase_time(self, time_s: int):
        """
        Increases block timestamp offset
        """
        self.block_timestamp_offset += time_s

    def set_next_block_time(self, time_s: int):
        """
        Sets the timestamp of next block
        """
        self.next_block_start_time = time_s
