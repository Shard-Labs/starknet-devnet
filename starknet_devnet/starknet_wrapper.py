from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.compiler.compile import get_selector_from_name
from .util import StarknetDevnetException, TxStatus
from .adapt import adapt_output, adapt_calldata
from typing import List
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from enum import Enum

class Choice(Enum):
    CALL = "call"
    INVOKE = "invoke"

class StarknetWrapper:
    def __init__(self):
        self.address2contract = {}
        """Maps contract address to contract instance."""

        self.address2types = {}
        """Maps contract address to a dict of types (structs) used in that contract."""

        self.transactions = []
        """A chronological list of transactions."""

        self.starknet = None

    async def get_starknet(self):
        if not self.starknet:
            self.starknet = await Starknet.empty()
        return self.starknet

    def store_types(self, contract_address: str, abi):
        """
        Stores the types (structs) used in a contract.
        The types are read from `abi`, and stored to a global map under the key `contract_address` which is expected to be a hex string.
        """

        structs = [entry for entry in abi if entry["type"] == "struct"]
        type_dict = { struct["name"]: struct for struct in structs }
        self.address2types[contract_address] = type_dict

    async def deploy(self, contract_definition: ContractDefinition, constructor_calldata):
        """
        Deploys the contract whose definition is provided and returns deployment address in hex form.
        The other returned object is present to conform to a past version of call_or_invoke, but will be removed in future versions.
        """

        starknet = await self.get_starknet()
        contract = await starknet.deploy(
            contract_def=contract_definition,
            constructor_calldata=constructor_calldata
        )

        hex_address = hex(contract.contract_address)
        self.address2contract[hex_address] = contract

        self.store_types(hex_address, contract_definition.abi)

        return hex_address

    async def call_or_invoke(self, choice: Choice, contract_address: str, entry_point_selector: int, calldata: list, signature: List[int]):
        contract_address = hex(contract_address)
        if (contract_address not in self.address2contract):
            message = f"No contract at the provided address ({contract_address})."
            raise StarknetDevnetException(message=message)

        contract: StarknetContract = self.address2contract[contract_address]
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

        types = self.address2types[contract_address]
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

            if "block_id" in transaction:
                ret["block_id"] = transaction["block_id"]

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

    def store_deploy_transaction(self, contract_address: str, constructor_calldata: List[str]) -> str:
        new_id = len(self.transactions)
        hex_new_id = hex(new_id)
        transaction = {
            "block_id": new_id,
            "block_number": new_id,
            "status": TxStatus.PENDING.name,
            "transaction": {
                "constructor_calldata": constructor_calldata,
                "contract_address": contract_address,
                # contract_address_salt
                "transaction_hash": hex_new_id,
                "type": TransactionType.DEPLOY.name
            },
            "transaction_hash": hex_new_id,
            "transaction_index": 0 # always the first (and only) tx in the block
        }
        self.transactions.append(transaction)
        return hex_new_id

    def store_invoke_transaction(self, contract_address: str, calldata: List[str], entry_point_selector: str, status: TxStatus, error_message=None) -> str:
        new_id = len(self.transactions)
        hex_new_id = hex(new_id)
        transaction = {
            "block_id": new_id,
            "block_number": new_id,
            "status": status.name,
            "transaction": {
                "calldata": calldata, # TODO str(arg) for arg in calldata
                "contract_address": contract_address,
                "entry_point_selector": entry_point_selector,
                # entry_point_type
                "transaction_hash": hex_new_id,
                "type": TransactionType.INVOKE_FUNCTION.name,
            },
            "transaction_hash": hex_new_id,
            "transaction_index": 0 # always the first (and only) tx in the block
        }

        if status == TxStatus.REJECTED:
            transaction["transaction_failure_reason"] = {
                "code": StarknetErrorCode.TRANSACTION_FAILED.name,
                "error_message": error_message,
                "tx_id": new_id
            }

        self.transactions.append(transaction)
        return hex_new_id
