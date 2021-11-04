from flask import Flask, request, jsonify, abort
from flask.wrappers import Response
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Transaction
from starkware.starknet.compiler.compile import get_selector_from_name
from starkware.starkware_utils.error_handling import StarkErrorCode
from .util import TxStatus, parse_args

app = Flask(__name__)

address2contract = {}
"""Maps contract address to contract instance."""

address2types = {}
"""Maps contract address to a dict of types (structs) used in that contract."""

transactions = []
"""A chronological list of transactions."""

class StarknetWrapper:
    def __init__(self):
        self.starknet = None

    async def get_starknet(self):
        if not self.starknet:
            self.starknet = await Starknet.empty()
        return self.starknet

starknet_wrapper = StarknetWrapper()

@app.route("/is_alive", methods=["GET"])
@app.route("/gateway/is_alive", methods=["GET"])
@app.route("/feeder_gateway/is_alive", methods=["GET"])
def is_alive():
    return "Alive!!!"

async def deploy(contract_definition: ContractDefinition):
    """
    Deploys the contract whose definition is provided and returns deployment address in hex form.
    The other returned object is present to conform to a past version of call_or_invoke, but will be removed in future versions.
    """

    starknet = await starknet_wrapper.get_starknet()
    contract = await starknet.deploy(contract_def=contract_definition)
    hex_address = hex(contract.contract_address)
    address2contract[hex_address] = contract
    return hex_address, {}

def generate_complex(calldata, calldata_i: int, input_type: str, types):
    """
    Converts members of `calldata` to a more complex type specified by `input_type`:
    - puts members of a struct into a tuple
    - puts members of a tuple into a tuple

    The `calldata_i` is incremented according to how many `calldata` members were consumed.
    `types` is a dict that maps a type's name to its specification.

    Returns the `calldata` converted to the type specified by `input_type` (tuple if struct or tuple, number). Also returns the incremented `calldata_i`.
    """

    if input_type == "felt":
        return calldata[calldata_i], calldata_i + 1

    arr = []
    if input_type[0] == "(" and input_type[-1] == ")":
        members = input_type[1:-1].split(", ")
    else:
        if input_type not in types:
            raise ValueError(f"Unsupported type: {input_type}")
        struct = types[input_type]
        members = [x["type"] for x in struct["members"]]

    for member in members:
        generated_complex, calldata_i = generate_complex(calldata, calldata_i, member, types)
        arr.append(generated_complex)

    return tuple(arr), calldata_i

def adapt_calldata(calldata, expected_inputs, types):
    """
    Simulatenously iterates over `calldata` and `expected_inputs`.

    The `calldata` is converted to types specified by `expected_inputs`.

    `types` is a dict that maps a type's name to its specification.

    Returns a list representing adapted `calldata`.
    """

    last_name = None
    last_value = None
    calldata_i = 0
    adapted_calldata = []
    for input_entry in expected_inputs:
        input_name = input_entry["name"]
        input_type = input_entry["type"]
        if calldata_i >= len(calldata):
            if input_type == "felt*" and last_name == f"{input_name}_len" and last_value == 0:
                # This means that an empty array is provided.
                # Last element was array length (0), it's replaced with the array itself
                adapted_calldata[-1] = []
                continue
            else:
                abort(Response(f"Too few function arguments provided: {len(calldata)}.", 400))
        input_value = calldata[calldata_i]

        if input_type == "felt*":
            if last_name != f"{input_name}_len":
                abort(Response(f"Array size argument {last_name} must appear right before {input_name}.", 400))

            arr_length = int(last_value)
            arr = calldata[calldata_i : calldata_i + arr_length]
            if len(arr) < arr_length:
                abort(Response(f"Too few function arguments provided: {len(calldata)}.", 400))

            # last element was array length, it's replaced with the array itself
            adapted_calldata[-1] = arr
            calldata_i += arr_length

        elif input_type == "felt":
            adapted_calldata.append(input_value)
            calldata_i += 1

        else: # struct
            try:
                generated_complex, calldata_i = generate_complex(calldata, calldata_i, input_type, types)
            except ValueError as e:
                abort(Response(str(e), 400))
            adapted_calldata.append(generated_complex)

        last_name = input_name
        last_value = input_value

    return adapted_calldata

def adapt_output(received, ret):
    """
    Adapts the `received` object to format expected by client (list of hex strings).
    If `received` is an instance of `list`, it is understood that it corresponds to a felt*, so first its length is appended.
    If `received` is iterable, it is either a struct, a tuple or a felt*.
    Otherwise it is a `felt`.
    `ret` is recursively populated (and should probably be empty on first call).

    Example:
    >>> L = []; adapt_output((1, [5, 10]), L); print(L)
    ['0x1', '0x2', '0x5', '0xa']
    """

    if isinstance(received, list):
        ret.append(hex(len(received)))
    try:
        for el in received:
            adapt_output(el, ret)
    except TypeError:
        ret.append(hex(received))

async def call_or_invoke(choice, contract_address: str, entry_point_selector: int, calldata: list):
    contract_address = hex(contract_address)
    if (contract_address not in address2contract):
        abort(Response(f"No contract at the provided address ({contract_address}).", 400))

    contract: StarknetContract = address2contract[contract_address]
    for method_name in contract._abi_function_mapping:
        selector = get_selector_from_name(method_name)
        if selector == entry_point_selector:
            try:
                method = getattr(contract, method_name)
            except NotImplementedError:
                msg = f"{method_name} uses a currently not supported feature (such as providing structs)."
                abort(Response(msg, 400))
            function_abi = contract._abi_function_mapping[method_name]
            break
    else:
        abort(Response(f"Illegal method selector: {entry_point_selector}.", 400))

    types = address2types[contract_address]
    adapted_calldata = adapt_calldata(calldata, function_abi["inputs"], types)

    prepared = method(*adapted_calldata)
    called = getattr(prepared, choice)
    executed = await called()

    adapted_output = []
    adapt_output(executed.result, adapted_output)

    return { "result": adapted_output }

def is_transaction_hash_legal(transaction_hash: int) -> bool:
    return 0 <= transaction_hash < len(transactions)

def store_types(contract_address: str, abi):
    """
    Stores the types (structs) used in a contract.
    The types are read from `abi`, and stored to a global map under the key `contract_address` which is expected to be a hex string.
    """

    structs = [x for x in abi if x["type"] == "struct"]
    type_dict = { struct["name"]: struct for struct in structs }
    address2types[contract_address] = type_dict

def store_transaction(contract_address: str, tx_type: str) -> str:
    new_id = len(transactions)
    hex_new_id = hex(new_id)
    transaction = {
        "block_id": new_id,
        "block_number": new_id,
        "status": TxStatus.PENDING.name,
        "transaction": {
            "contract_address": contract_address,
            "type": tx_type
        },
        "transaction_hash": hex_new_id,
        "transaction_index": 0 # always the first (and only) tx in the block
    }
    transactions.append(transaction)
    return hex_new_id

@app.route("/gateway/add_transaction", methods=["POST"])
async def add_transaction():
    """
    Endpoint for accepting DEPLOY and INVOKE_FUNCTION transactions.
    """

    raw_data = request.get_data()
    transaction = Transaction.loads(raw_data)
    # TODO transaction.calculate_hash()

    tx_type = transaction.tx_type.name
    result_dict = {}
    if tx_type == "DEPLOY":
        contract_address, result_dict = await deploy(
            transaction.contract_definition
        )
        store_types(contract_address, transaction.contract_definition.abi)
    elif tx_type == "INVOKE_FUNCTION":
        contract_address = hex(transaction.contract_address)
        result_dict = await call_or_invoke("invoke",
            contract_address=transaction.contract_address,
            entry_point_selector=transaction.entry_point_selector,
            calldata=transaction.calldata
        )
    else:
        abort(Response(f"Invalid tx_type: {tx_type}.", 400))

    transaction_hash = store_transaction(contract_address, tx_type)

    return jsonify({
        "code": StarkErrorCode.TRANSACTION_RECEIVED.name,
        "transaction_hash": transaction_hash,
        "address": contract_address,
        **result_dict
    })

@app.route("/feeder_gateway/get_contract_addresses", methods=["GET"])
def get_contract_addresses():
    return "Not implemented", 501

@app.route("/feeder_gateway/call_contract", methods=["POST"])
async def call_contract():
    """
    Endpoint for receiving calls (not invokes) of contract functions.
    """

    raw_data = request.get_data()
    call_specifications = InvokeFunction.loads(raw_data)
    result_dict = await call_or_invoke("call",
        contract_address=call_specifications.contract_address,
        entry_point_selector=call_specifications.entry_point_selector,
        calldata=call_specifications.calldata
    )
    return jsonify(result_dict)

@app.route("/feeder_gateway/get_block", methods=["GET"])
def get_block():
    block_id = request.args.get("blockId", type=int)
    print(block_id)
    return "Not implemented", 501

@app.route("/feeder_gateway/get_code", methods=["GET"])
def get_code():
    block_id = request.args.get("blockId", type=int)
    print(block_id)

    contract_address = request.args.get("contractAddress", type=int)
    print(contract_address)
    return "Not implemented", 501

@app.route("/feeder_gateway/get_storage_at", methods=["GET"])
def get_storage_at():
    contract_address = request.args.get("contractAddress", type=int)
    print(contract_address)

    key = request.args.get("key")
    print(key)

    block_id = request.args.get("blockId", type=int)
    print(block_id)
    return "Not implemented", 501

@app.route("/feeder_gateway/get_transaction_status", methods=["GET"])
def get_transaction_status():
    transaction_hash = request.args.get("transactionHash", type=lambda x: int(x, 16))
    tx_status = (
        TxStatus.PENDING.name
        if is_transaction_hash_legal(transaction_hash)
        else TxStatus.NOT_RECEIVED.name
    )
    return jsonify({
        "tx_status": tx_status
    })

@app.route("/feeder_gateway/get_transaction", methods=["GET"])
def get_transaction():
    """
    Returns the transaction identified by the transactionHash argument in the GET request.
    """

    transaction_hash = request.args.get("transactionHash", type=lambda x: int(x, 16))
    if is_transaction_hash_legal(transaction_hash):
        return jsonify(transactions[transaction_hash])
    else:
        return jsonify({
            "status": TxStatus.NOT_RECEIVED.name,
            "transaction_hash": transaction_hash
        })

def main():
    args = parse_args()
    app.run(**vars(args))

if __name__ == "__main__":
    main()
