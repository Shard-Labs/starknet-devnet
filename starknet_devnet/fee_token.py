"""
Fee token and its predefined constants.
"""

from starkware.solidity.utils import load_nearby_contract
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.business_logic.state.objects import ContractState, ContractCarriedState
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.starknet import Starknet
from starkware.python.utils import to_bytes

from starknet_devnet.util import Uint256

class FeeToken:
    """Wrapper of token for charging fees."""

    DEFINITION: ContractDefinition = None # loaded lazily

    # Precalcuated to save time
    # HASH = to_bytes(compute_contract_hash(contract_definition=FeeToken.get_definition()))
    HASH = 375899817338126263298463755162657787890597705735749339531748983767835688120
    HASH_BYTES = to_bytes(HASH)

    # Random value to fix the token contract address
    SALT = 10
    CONSTRUCTOR_CALLDATA = []

    # Precalculated to save time
    # ADDRESS = calculate_contract_address_from_hash(salt=SALT, contract_hash=HASH,
    #     constructor_calldata=CONSTRUCTOR_CALLDATA,
    #     caller_address=0
    # )
    ADDRESS = 3010087218464233437042494926438213308193618470717965319183989869245145381251

    contract: StarknetContract = None

    @classmethod
    def get_definition(cls):
        """Returns contract definition via lazy loading."""
        if not cls.DEFINITION:
            cls.DEFINITION = ContractDefinition.load(load_nearby_contract("ERC20"))
        return cls.DEFINITION

    @classmethod
    async def deploy(cls, starknet: Starknet):
        """Deploy token contract for charging fees."""

        fee_token_carried_state = starknet.state.state.contract_states[cls.ADDRESS]
        fee_token_state = fee_token_carried_state.state
        assert not fee_token_state.initialized

        starknet.state.state.contract_definitions[cls.HASH_BYTES] = cls.get_definition()
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
            }
        )

        cls.contract = StarknetContract(
            state=starknet.state,
            abi=cls.get_definition().abi,
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
