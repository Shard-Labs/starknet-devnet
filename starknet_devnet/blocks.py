"""
Class for generating and handling blocks
"""

from typing import Dict, Tuple

from starkware.starknet.testing.state import StarknetState
from starkware.starknet.services.api.feeder_gateway.block_hash import calculate_block_hash

from .origin import Origin
from .util import (
    StarknetDevnetException,
    TxStatus,
    fixed_length_hex
)
from .transaction_wrapper import TransactionWrapper

class DevnetBlocks():
    """This class is used to store the generated blocks of the devnet."""

    def __init__(self, origin: Origin, lite = False) -> None:
        self.origin = origin
        self.__num2block = {}
        self.__state_updates = {}
        self.__hash2num = {}
        self.lite = lite

    def __get_last_block(self):
        """Returns the last block stored so far."""
        number_of_blocks = self.get_number_of_blocks()
        return self.get_by_number(number_of_blocks - 1)

    def get_number_of_blocks(self) -> int:
        """Returns the number of blocks stored so far."""
        return len(self.__num2block) + self.origin.get_number_of_blocks()

    def get_by_number(self, block_number: int) -> Dict:
        """Returns the block whose block_number is provided"""
        if block_number is None:
            if self.__num2block:
                return self.__get_last_block()
            return self.origin.get_block_by_number(block_number)

        if block_number < 0:
            message = f"Block number must be a non-negative integer; got: {block_number}."
            raise StarknetDevnetException(message=message)

        if block_number >= self.get_number_of_blocks():
            message = f"Block number too high. There are currently {len(self.__num2block)} blocks; got: {block_number}."
            raise StarknetDevnetException(message=message)

        if block_number in self.__num2block:
            return self.__num2block[block_number]

        return self.origin.get_block_by_number(block_number)

    def get_by_hash(self, block_hash: str) -> Dict:
        """
        Returns the block with the given block hash.
        """
        numeric_hash = int(block_hash, 16)

        if numeric_hash in self.__hash2num:
            block_number = self.__hash2num[int(block_hash, 16)]
            return self.get_by_number(block_number)

        return self.origin.get_block_by_hash(block_hash)

    def get_state_update(self, block_hash=None, block_number=None):
        """
        Returns state update for the provided block hash or block number.
        It will return the last state update if block is not provided.
        """
        if block_hash:
            numeric_hash = int(block_hash, 16)

            if numeric_hash not in self.__hash2num:
                return self.origin.get_state_update(block_hash=block_hash)

            block_number = self.__hash2num[numeric_hash]

        if block_number is not None:
            if block_number not in self.__state_updates:
                return self.origin.get_state_update(block_number=block_number)

            return self.__state_updates[block_number]


        return self.__state_updates.get(self.get_number_of_blocks() - 1) or self.origin.get_state_update()

    async def generate(
        self, tx_wrapper: TransactionWrapper, state: StarknetState,
        state_root: bytes, state_update = None
    ) -> Tuple[str, int]:
        """
        Generates a block and stores it to blocks and hash2block. The block contains just the passed transaction.
        The `tx_wrapper.transaction` dict should contain a key `transaction`.
        Returns (block_hash, block_number).
        """
        block_number = self.get_number_of_blocks()
        timestamp = state.state.block_info.block_timestamp
        signature = []
        if "signature" in tx_wrapper.transaction["transaction"]:
            signature = [int(sig_part, 16) for sig_part in tx_wrapper.transaction["transaction"]["signature"]]

        parent_block_hash = self.__get_last_block()["block_hash"] if block_number else fixed_length_hex(0)
        sequencer_address = state.general_config.sequencer_address
        gas_price = state.general_config.min_gas_price

        if self.lite:
            block_hash = block_number
        else:
            block_hash = await calculate_block_hash(
                general_config=state.general_config,
                parent_hash=int(parent_block_hash, 16),
                block_number=block_number,
                global_state_root=state_root,
                block_timestamp=timestamp,
                tx_hashes=[int(tx_wrapper.transaction_hash, 16)],
                tx_signatures=[signature],
                event_hashes=[],
                sequencer_address=state.general_config.sequencer_address
            )

        block_hash_hexed = fixed_length_hex(block_hash)
        block = {
            "block_hash": block_hash_hexed,
            "block_number": block_number,
            "gas_price": hex(gas_price),
            "parent_block_hash": parent_block_hash,
            "sequencer_address": hex(sequencer_address),
            "state_root": state_root.hex(),
            "status": TxStatus.ACCEPTED_ON_L2.name,
            "timestamp": timestamp,
            "transaction_receipts": [tx_wrapper.get_receipt_block_variant()],
            "transactions": [tx_wrapper.transaction["transaction"]],
        }

        self.__num2block[block_number] = block
        self.__hash2num[block_hash] = block_number

        if state_update is not None:
            state_update["block_hash"] = hex(block_hash)

        self.__state_updates[block_number] = state_update

        return block_hash_hexed, block_number
