from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.compiler.compile import get_selector_from_name
from starkware.starknet.testing.state import CastableToAddressSalt
from .util import StarknetDevnetException, TxStatus, fixed_length_hex
from .adapt import adapt_output, adapt_calldata
from .contract_wrapper import ContractWrapper
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

        self.starknet = None

    async def get_starknet(self):
        if not self.starknet:
            self.starknet = await Starknet.empty()
        return self.starknet

    async def get_state(self):
        if not self.starknet:
            self.starknet = await Starknet.empty()
        return self.starknet.state

    def contract_deployed(self, address: int) -> bool:
        return address in self.address2contract_wrapper

    def get_contract_wrapper(self, address: int) -> ContractWrapper:
        # TODO use default Starknet.state
        if (not self.contract_deployed(address)):
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

        self.address2contract_wrapper[contract.contract_address] = ContractWrapper(contract, contract_definition)

    async def call_or_invoke(self, choice: Choice, contract_address: int, entry_point_selector: int, calldata: list, signature: List[int]):
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

    def store_transaction(self, contract_address: str, status: TxStatus, error_message: str=None, **transaction_details: dict):
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
            transaction["block_hash"] = hex_new_id
            transaction["block_number"] = new_id

        self.transactions.append(transaction)
        return hex_new_id

    def store_deploy_transaction(self, contract_address: str, calldata: List[str], salt: str, status: TxStatus, error_message: str=None) -> str:
        return self.store_transaction(
            contract_address,
            status,
            error_message,
            type=TransactionType.DEPLOY.name,
            constructor_calldata=calldata,
            contract_address_salt=salt
        )

    def store_invoke_transaction(self, contract_address: str, calldata: List[str], entry_point_selector: str, status: TxStatus, error_message: str=None) -> str:
        return self.store_transaction(
            contract_address,
            status,
            error_message,
            type=TransactionType.INVOKE_FUNCTION.name,
            calldata=calldata,
            entry_point_selector=entry_point_selector,
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
