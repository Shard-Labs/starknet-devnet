"""
Account class and its predefined constants.
"""

from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.solidity.utils import load_nearby_contract
from starkware.starknet.business_logic.state.objects import ContractState, ContractCarriedState
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.services.api.gateway.contract_address import calculate_contract_address_from_hash
from starkware.starknet.storage.starknet_storage import StorageLeaf
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.testing.contract import StarknetContract
from starkware.python.utils import to_bytes

from starknet_devnet.util import Uint256

class Account:
    """Account contract wrapper."""

    DEFINITION: ContractDefinition = None # loaded lazily
    CONTRACT_PATH = "accounts_artifacts/OpenZeppelin/0.1.0/Account.cairo/Account"

    # Precalculated to save time
    # HASH = compute_contract_hash(contract_definition=Account.get_definition()))
    HASH = 361479646297615797917493841430922492724680358320444679508058603177506550951
    HASH_BYTES = to_bytes(HASH)

    # Random value to make the constructor_calldata the only thing that affects the account address
    SALT = 20

    def __init__(self, private_key: int, public_key: int, initial_balance: int):
        self.private_key = private_key
        self.public_key = public_key
        self.address = calculate_contract_address_from_hash(
            salt=Account.SALT,
            contract_hash=Account.HASH,
            constructor_calldata=[public_key],
            caller_address=0
        )
        self.initial_balance = initial_balance

    @classmethod
    def get_definition(cls):
        """Returns contract definition via lazy loading."""
        if not cls.DEFINITION:
            cls.DEFINITION = ContractDefinition.load(load_nearby_contract(cls.CONTRACT_PATH))
        return cls.DEFINITION

    async def deploy(self, starknet: Starknet) -> StarknetContract:
        """Deploy this account."""
        account_carried_state = starknet.state.state.contract_states[self.address]
        account_state = account_carried_state.state
        assert not account_state.initialized

        starknet.state.state.contract_definitions[Account.HASH_BYTES] = Account.get_definition()

        newly_deployed_account_state = await ContractState.create(
            contract_hash=Account.HASH_BYTES,
            storage_commitment_tree=account_state.storage_commitment_tree
        )

        starknet.state.state.contract_states[self.address] = ContractCarriedState(
            state=newly_deployed_account_state,
            storage_updates={
                get_selector_from_name("Account_public_key"): StorageLeaf(self.public_key)
            }
        )

        # set initial balance
        fee_token_address = starknet.state.general_config.fee_token_address
        fee_token_storage_updates = starknet.state.state.contract_states[fee_token_address].storage_updates

        balance_address = pedersen_hash(get_selector_from_name("ERC20_balances"), self.address)
        initial_balance_uint256 = Uint256.from_felt(self.initial_balance)
        fee_token_storage_updates[balance_address] = StorageLeaf(initial_balance_uint256.low)
        fee_token_storage_updates[balance_address + 1] = StorageLeaf(initial_balance_uint256.high)

        return StarknetContract(
            state=starknet.state,
            abi=Account.get_definition().abi,
            contract_address=self.address,
            deploy_execution_info=None
        )
