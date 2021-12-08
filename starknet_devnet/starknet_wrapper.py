import time
from starkware.starknet.business_logic.state import CarriedState
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.compiler.compile import get_selector_from_name
from starkware.starknet.testing.state import CastableToAddressSalt
from .util import StarknetDevnetException, TxStatus, fixed_length_hex
from .adapt import adapt_output, adapt_calldata
from .contract_wrapper import ContractWrapper
from copy import deepcopy
from typing import List, Dict
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from enum import Enum

class Choice(Enum):
    CALL = "call"
    INVOKE = "invoke"

class StarknetWrapper:
    def __init__(self):
        self.address2contract_wrapper: Dict[int, ContractWrapper] = {}
        """Maps contract address to contract wrapper."""

        self.transactions = []
        """A chronological list of transactions."""

        self.hash2block = {}
        """Maps block hash to block."""

        self.blocks = []
        """A chronological list of blocks (one transaction per block)."""

        self.starknet = None

        self.current_carried_state = None

    async def preserve_current_state(self, state: CarriedState):
        self.current_carried_state = deepcopy(state)
        self.current_carried_state.shared_state = state.shared_state

    async def get_starknet(self):
        if not self.starknet:
            self.starknet = await Starknet.empty()
            await self.preserve_current_state(self.starknet.state.state)
        return self.starknet

    async def get_state(self):
        starknet = await self.get_starknet()
        return starknet.state
    
    async def update_state(self):
        previous_state = self.current_carried_state
        assert previous_state is not None
        current_carried_state = (await self.get_state()).state
        updated_shared_state = await current_carried_state.shared_state.apply_state_updates(
            ffc=current_carried_state.ffc,
            previous_carried_state=previous_state,
            current_carried_state=current_carried_state
        )
        self.starknet.state.state.shared_state = updated_shared_state
        await self.preserve_current_state(self.starknet.state.state)
        # await self.preserve_carried_state(current_carried_state)

    async def get_state_root(self):
        state = await self.get_state()
        return state.state.shared_state.contract_states.root.hex()

    def contract_deployed(self, address: int) -> bool:
        return address in self.address2contract_wrapper

    def get_contract_wrapper(self, address: int) -> ContractWrapper:
        # TODO use default Starknet.state
        if not self.contract_deployed(address):
            message = f"No contract at the provided address ({fixed_length_hex(address)})."
            raise StarknetDevnetException(message=message)

        return self.address2contract_wrapper[address]

    async def deploy(self, contract_definition: ContractDefinition, contract_address_salt: CastableToAddressSalt, constructor_calldata: List[int]):
        """
        Deploys the contract whose definition is provided and returns deployment address in hex form.
        The other returned object is present to conform to a past version of call_or_invoke, but will be removed in future versions.
        """

        starknet = await self.get_starknet()
        contract = await starknet.deploy(
            contract_def=contract_definition,
            constructor_calldata=constructor_calldata,
            contract_address_salt=contract_address_salt
        )
        await self.update_state()

        self.address2contract_wrapper[contract.contract_address] = ContractWrapper(contract, contract_definition)

    async def call_or_invoke(self, choice: Choice, contract_address: int, entry_point_selector: int, calldata: List[int], signature: List[int]):
        contract = self.get_contract_wrapper(contract_address).contract
        for method_name in contract._abi_function_mapping:
            selector = get_selector_from_name(method_name)
            if selector == entry_point_selector:
                try:
                    method = getattr(contract, method_name)
                except NotImplementedError:
                    message = f"{method_name} uses a currently not supported feature (such as providing structs)."
                    raise StarknetDevnetException(message=message)
                function_abi = contract._abi_function_mapping[method_name]
                break
        else:
            message = f"Illegal method selector: {entry_point_selector}."
            raise StarknetDevnetException(message=message)

        types = self.get_contract_wrapper(contract_address).types
        adapted_calldata = adapt_calldata(calldata, function_abi["inputs"], types)

        prepared = method(*adapted_calldata)
        called = getattr(prepared, choice.value)
        executed = await called(signature=signature)
        await self.update_state()

        adapted_output = adapt_output(executed.result)
        return { "result": adapted_output }

    def is_transaction_hash_legal(self, transaction_hash_int: int) -> bool:
        return 0 <= transaction_hash_int < len(self.transactions)

    def get_transaction_status(self, transaction_hash: str):
        transaction_hash_int = int(transaction_hash, 16)

        if self.is_transaction_hash_legal(transaction_hash_int):
            transaction = self.transactions[transaction_hash_int]
            ret = {
                "tx_status": transaction["status"]
            }

            if "block_hash" in transaction:
                ret["block_hash"] = transaction["block_hash"]

            failure_key = "transaction_failure_reason"
            if failure_key in transaction:
                ret[failure_key] = transaction[failure_key]

            return ret

        return {
            "tx_status": TxStatus.NOT_RECEIVED.name
        }

    def get_transaction(self, transaction_hash: str):
        transaction_hash_int = int(transaction_hash, 16)
        if self.is_transaction_hash_legal(transaction_hash_int):
            return self.transactions[transaction_hash_int]
        return {
            "status": TxStatus.NOT_RECEIVED.name,
            "transaction_hash": transaction_hash
        }

    async def generate_block(self, transaction: dict):
        """
        Generates a block and stores it to blocks and hash2block. The block contains just the passed transaction.

        Returns (block_hash, block_number)
        """

        block_number = len(self.blocks)
        block_hash = hex(block_number)
        state_root = await self.get_state_root()

        block = {
            "block_hash": block_hash,
            "block_number": block_number,
            "parent_block_hash": self.blocks[-1]["block_hash"] if self.blocks else "0x0",
            "state_root": state_root,
            "status": TxStatus.ACCEPTED_ON_L2.name,
            "timestamp": int(time.time()),
            "transaction_receipts": ["Not yet supported!"], # TODO
            "transactions": [transaction],
        }

        self.blocks.append(block)
        self.hash2block[int(block_hash, 16)] = block
        return block_hash, block_number

    def get_block(self, block_hash: str=None, block_number: int=None):
        if block_hash is not None and block_number is not None:
            message = f"Ambiguous criteria: only one of (block number, block hash) can be provided."
            raise StarknetDevnetException(message=message)

        if block_hash is not None:
            block_hash_int = int(block_hash, 16)
            if block_hash_int in self.hash2block:
                return self.hash2block[block_hash_int]
            message = f"Block hash not found; got: {block_hash}."
            raise StarknetDevnetException(message=message)

        if block_number is not None:
            if block_number < 0:
                message = f"Block number must be a non-negative integer; got: {block_number}."
                raise StarknetDevnetException(message=message)

            if block_number >= len(self.blocks):
                message = f"Block number too high. There are currently {len(self.blocks)} blocks; got: {block_number}."
                raise StarknetDevnetException(message=message)

            return self.blocks[block_number]
        
        # no block identifier means latest block
        if self.blocks:
            return self.blocks[-1]
        message = f"Requested the latest block, but there are no blocks so far."
        raise StarknetDevnetException(message=message)

    async def store_transaction(self, contract_address: str, status: TxStatus, error_message: str=None, **transaction_details: dict):
        new_id = len(self.transactions)
        hex_new_id = hex(new_id)

        transaction = {
            "status": status.name,
            "transaction": {
                "contract_address": fixed_length_hex(contract_address),
                "transaction_hash": hex_new_id,
                **transaction_details
            },
            "transaction_index": 0 # always the first (and only) tx in the block
        }

        if status == TxStatus.REJECTED:
            transaction["transaction_failure_reason"] = {
                "code": StarknetErrorCode.TRANSACTION_FAILED.name,
                "error_message": error_message,
                "tx_id": new_id
            }
        else:
            block_hash, block_number = await self.generate_block(transaction["transaction"])
            transaction["block_hash"] = block_hash
            transaction["block_number"] = block_number

        self.transactions.append(transaction)
        return hex_new_id

    async def store_deploy_transaction(self, contract_address: str, calldata: List[int], salt: int, status: TxStatus, error_message: str=None):
        return await self.store_transaction(
            contract_address,
            status,
            error_message,
            type=TransactionType.DEPLOY.name,
            constructor_calldata=[str(arg) for arg in calldata],
            contract_address_salt=hex(salt)
        )

    async def store_invoke_transaction(self, contract_address: str, calldata: List[int], entry_point_selector: int, status: TxStatus, error_message: str=None):
        return await self.store_transaction(
            contract_address,
            status,
            error_message,
            type=TransactionType.INVOKE_FUNCTION.name,
            calldata=[str(arg) for arg in calldata],
            entry_point_selector=str(entry_point_selector),
            # entry_point_type
        )

    def get_code(self, contract_address: int) -> dict:
        if self.contract_deployed(contract_address):
            contract_wrapper = self.get_contract_wrapper(contract_address)
            return contract_wrapper.code
        return {
            "abi": {},
            "bytecode": []
        }

    async def get_storage_at(self, contract_address: int, key: int) -> str:
        state = await self.get_state()
        contract_states = state.state.contract_states

        state = contract_states[contract_address]
        if key in state.storage_updates:
            return hex(state.storage_updates[key].value)
        return hex(0)
