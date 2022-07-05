"""
Fee token and its predefined constants.
"""

from starkware.solidity.utils import load_nearby_contract
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starknet.storage.starknet_storage import StorageLeaf
from starkware.starknet.business_logic.state.objects import (ContractState, ContractCarriedState)
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.starknet import Starknet
from starkware.python.utils import to_bytes
from starkware.starknet.compiler.compile import get_selector_from_name
from starknet_devnet.util import Uint256

class FeeToken:
    """Wrapper of token for charging fees."""

    CONTRACT_CLASS: ContractClass = None # loaded lazily

    # Precalcuated to save time
    # HASH = to_bytes(compute_class_hash(contract_class=FeeToken.get_contract_class()))
    HASH = 3000409729603134799471314790024123407246450023546294072844903167350593031855
    HASH_BYTES = to_bytes(HASH)

    # Random value to fix the token contract address
    SALT = 10
    CONSTRUCTOR_CALLDATA = []

    # Precalculated to save time
    # ADDRESS = calculate_contract_address_from_hash(salt=SALT, class_hash=HASH,
    #     constructor_calldata=CONSTRUCTOR_CALLDATA,
    #     caller_address=0
    # )
    ADDRESS = 2774287484619332564597403632816768868845110259953541691709975889937073775752

    contract: StarknetContract = None

    @classmethod
    def get_contract_class(cls):
        """Returns contract class via lazy loading."""
        if not cls.CONTRACT_CLASS:
            cls.CONTRACT_CLASS = ContractClass.load(load_nearby_contract("ERC20_Mintable_OZ_0.2.0"))
        return cls.CONTRACT_CLASS

    @classmethod
    async def deploy(cls, starknet: Starknet):
        """Deploy token contract for charging fees."""

        fee_token_carried_state = starknet.state.state.contract_states[cls.ADDRESS]
        fee_token_state = fee_token_carried_state.state
        assert not fee_token_state.initialized

        starknet.state.state.contract_definitions[cls.HASH_BYTES] = cls.get_contract_class()
        newly_deployed_fee_token_state = await ContractState.create(
            contract_hash=cls.HASH_BYTES,
            storage_commitment_tree=fee_token_state.storage_commitment_tree
        )

        starknet.state.state.contract_states[cls.ADDRESS] = ContractCarriedState(
            state=newly_deployed_fee_token_state,
            storage_updates={
                # Running the constructor doesn't need to be simulated
                # If it was, it would be done like this:
                # get_selector_from_name("ERC20_name_"): StorageLeaf(42)
                get_selector_from_name('ERC20_name'): StorageLeaf(int.from_bytes(bytes('DevnetST', "ascii"), "big")),
                get_selector_from_name('ERC20_symbol'): StorageLeaf(int.from_bytes(bytes('DST', "ascii"), "big")),
                get_selector_from_name('ERC20_decimals'): StorageLeaf(18)
            }
        )

        cls.contract = StarknetContract(
            state=starknet.state,
            abi=cls.get_contract_class().abi,
            contract_address=cls.ADDRESS,
            deploy_execution_info=None
        )

    @classmethod
    async def get_balance(cls, address: int) -> int:
        """Return the balance of the contract under `address`."""
        assert cls.contract
        response = await cls.contract.balanceOf(address).call()

        balance = Uint256(
            low=response.result.balance.low,
            high=response.result.balance.high
        ).to_felt()
        return balance

    @classmethod
    async def mint_lite(cls, to_address: str, amount: int) -> None:
        """Mint `amount` of token at `address`."""
        assert cls.contract
        amount_uint256 = Uint256.from_felt(amount)
        return await cls.contract.mint(int(to_address, 16), (amount_uint256.low, amount_uint256.high)).invoke()

    @classmethod
    async def mint(cls, to_address: str, amount: int, starknet_wrapper) -> None:
        """Mint with internal transaction"""
        assert cls.contract
        amount_uint256 = Uint256.from_felt(amount)

        transaction_data = {
            "entry_point_selector": hex(get_selector_from_name("mint")),
            "calldata": [
                str(int(to_address, 0)),
                str(amount_uint256.low),
                str(amount_uint256.high),
            ],
            "signature": [],
            "contract_address": hex(cls.ADDRESS)
        }
        transaction = InvokeFunction.load(transaction_data)
        return await starknet_wrapper.invoke(transaction)
