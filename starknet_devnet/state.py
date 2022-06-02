"""
Global state singletone
"""

import random
import sys

from starkware.crypto.signature.signature import private_to_stark_key

from .account import Account
from .dump import Dumper
from .starknet_wrapper import StarknetWrapper, DevnetConfig

class State():
    """
    Stores starknet wrapper and dumper
    """
    def __init__(self):
        self.starknet_wrapper = StarknetWrapper(config=DevnetConfig())
        self.dumper = Dumper(self.starknet_wrapper)

    def __set_starknet_wrapper(self, starknet_wrapper: StarknetWrapper):
        """Sets starknet wrapper and creates new instance of dumper"""
        self.starknet_wrapper = starknet_wrapper
        self.dumper = Dumper(starknet_wrapper)

    async def reset(self, config: DevnetConfig = None):
        """Reset the starknet wrapper and dumper instances"""
        previous_config = self.starknet_wrapper.config
        self.__set_starknet_wrapper(StarknetWrapper(config=config or previous_config))
        await self.starknet_wrapper.initialize()

    def load(self, load_path: str):
        """Loads starknet wrapper from path"""
        self.__set_starknet_wrapper(StarknetWrapper.load(load_path))

    def generate_accounts(self, n_accounts: int, initial_balance: int, seed: int):
        """Generates accounts without deploying them"""
        random_generator = random.Random()

        if seed is None:
            seed = random_generator.getrandbits(32)
        random_generator.seed(seed)

        accounts = []
        for i in range(n_accounts):
            private_key = random_generator.getrandbits(128)
            public_key = private_to_stark_key(private_key)

            account = Account(
                private_key=private_key,
                public_key=public_key,
                initial_balance=initial_balance
            )
            accounts.append(account)

            print(f"Account #{i}")
            print(f"Address: {hex(account.address)}")
            print(f"Public key: {hex(account.public_key)}")
            print(f"Private key: {hex(account.private_key)}")
            print()

        self.starknet_wrapper.accounts = accounts

        print(f"Initial balance of each account: {initial_balance} WEI")
        print("Seed to replicate this account sequence:", seed)
        print(
            "WARNING: Use these accounts and their keys ONLY for local testing. "
            "DO NOT use them on mainnet or other live networks because you will LOSE FUNDS.",
            file=sys.stderr
        )
        print()

state = State()
