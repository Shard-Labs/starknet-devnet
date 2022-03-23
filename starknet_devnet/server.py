"""
A server exposing Starknet functionalities as API endpoints.
"""

import os
import json
import signal
import sys
import dill as pickle

from flask import Flask, request, jsonify, abort
from flask.wrappers import Response
from flask_cors import CORS
from marshmallow import ValidationError
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Transaction
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.error_handling import StarkErrorCode, StarkException
from werkzeug.datastructures import MultiDict

from .constants import CAIRO_LANG_VERSION
from .dump import Dumper
from .starknet_wrapper import StarknetWrapper
from .util import DumpOn, StarknetDevnetException, custom_int, fixed_length_hex, parse_args

app = Flask(__name__)
CORS(app)

@app.route("/is_alive", methods=["GET"])
@app.route("/gateway/is_alive", methods=["GET"])
@app.route("/feeder_gateway/is_alive", methods=["GET"])
def is_alive():
    """Health check endpoint."""
    return "Alive!!!"

@app.route("/gateway/add_transaction", methods=["POST"])
async def add_transaction():
    """Endpoint for accepting DEPLOY and INVOKE_FUNCTION transactions."""

    transaction = validate_transaction(request.data)
    tx_type = transaction.tx_type.name

    if tx_type == TransactionType.DEPLOY.name:
        contract_address, transaction_hash = await starknet_wrapper.deploy(transaction)
        result_dict = {}
    elif tx_type == TransactionType.INVOKE_FUNCTION.name:
        try:
            contract_address, transaction_hash, result_dict = await starknet_wrapper.invoke(transaction)
        except StarkException as stark_exception:
            abort(Response(stark_exception.message, 500))
    else:
        abort(Response(f"Invalid tx_type: {tx_type}.", 400))

    # after tx
    if dumper.dump_on == DumpOn.TRANSACTION:
        dumper.dump()

    return jsonify({
        "code": StarkErrorCode.TRANSACTION_RECEIVED.name,
        "transaction_hash": hex(transaction_hash),
        "address": fixed_length_hex(contract_address),
        **result_dict
    })

def validate_transaction(data: bytes, loader: Transaction=Transaction):
    """Ensure `data` is a valid Starknet transaction. Returns the parsed `Transaction`."""
    try:
        transaction = loader.loads(data)
    except (TypeError, ValidationError) as err:
        msg = f"Invalid tx: {err}\nBe sure to use the correct compilation (json) artifact. Devnet-compatible cairo-lang version: {CAIRO_LANG_VERSION}"
        abort(Response(msg, 400))
    return transaction

@app.route("/feeder_gateway/get_contract_addresses", methods=["GET"])
def get_contract_addresses():
    """Endpoint that returns an object containing the addresses of key system components."""
    return "Not implemented", 501

@app.route("/feeder_gateway/call_contract", methods=["POST"])
async def call_contract():
    """
    Endpoint for receiving calls (not invokes) of contract functions.
    """

    call_specifications = validate_call(request.data)

    try:
        result_dict = await starknet_wrapper.call(call_specifications)
    except StarkException as err:
        # code 400 would make more sense, but alpha returns 500
        abort(Response(err.message, 500))

    return jsonify(result_dict)

def validate_call(data: bytes):
    """Ensure `data` is valid Starknet function call. Returns an `InvokeFunction`."""

    try:
        call_specifications = InvokeFunction.loads(data)
    except (TypeError, ValidationError) as err:
        abort(Response(f"Invalid Starknet function call: {err}", 400))

    return call_specifications

def _check_block_hash(request_args: MultiDict):
    block_hash = request_args.get("blockHash", type=custom_int)
    if block_hash is not None:
        print("Specifying a block by its hash is not supported. All interaction is done with the latest block.")

def _check_block_arguments(block_hash, block_number):
    if block_hash is not None and block_number is not None:
        message = "Ambiguous criteria: only one of (block number, block hash) can be provided."
        abort(Response(message, 500))

@app.route("/feeder_gateway/get_block", methods=["GET"])
async def get_block():
    """Endpoint for retrieving a block identified by its hash or number."""
    block_hash = request.args.get("blockHash")
    block_number = request.args.get("blockNumber", type=custom_int)

    _check_block_arguments(block_hash, block_number)

    try:
        if block_hash is not None:
            result_dict = starknet_wrapper.get_block_by_hash(block_hash)
        else:
            result_dict = starknet_wrapper.get_block_by_number(block_number)
    except StarkException as err:
        abort(Response(err.message, 500))

    return jsonify(result_dict)

@app.route("/feeder_gateway/get_code", methods=["GET"])
def get_code():
    """
    Returns the ABI and bytecode of the contract whose contractAddress is provided.
    """

    _check_block_hash(request.args)

    contract_address = request.args.get("contractAddress", type=custom_int)
    result_dict = starknet_wrapper.get_code(contract_address)
    return jsonify(result_dict)

@app.route("/feeder_gateway/get_full_contract", methods=["GET"])
def get_full_contract():
    """
    Returns the contract definition of the contract whose contractAddress is provided.
    """
    _check_block_hash(request.args)

    contract_address = request.args.get("contractAddress", type=custom_int)

    try:
        result_dict = starknet_wrapper.get_full_contract(contract_address)
    except StarknetDevnetException as error:
        # alpha throws 500 for unitialized contracts
        abort(Response(error.message, 500))
    return jsonify(result_dict)

@app.route("/feeder_gateway/get_storage_at", methods=["GET"])
async def get_storage_at():
    """Endpoint for returning the storage identified by `key` from the contract at """
    _check_block_hash(request.args)

    contract_address = request.args.get("contractAddress", type=custom_int)
    key = request.args.get("key", type=custom_int)

    storage = await starknet_wrapper.get_storage_at(contract_address, key)
    return jsonify(storage)

@app.route("/feeder_gateway/get_transaction_status", methods=["GET"])
def get_transaction_status():
    """
    Returns the status of the transaction identified by the transactionHash argument in the GET request.
    """

    transaction_hash = request.args.get("transactionHash")
    ret = starknet_wrapper.get_transaction_status(transaction_hash)
    return jsonify(ret)

@app.route("/feeder_gateway/get_transaction", methods=["GET"])
def get_transaction():
    """
    Returns the transaction identified by the transactionHash argument in the GET request.
    """

    transaction_hash = request.args.get("transactionHash")
    ret = starknet_wrapper.get_transaction(transaction_hash)
    return jsonify(ret)

@app.route("/feeder_gateway/get_transaction_receipt", methods=["GET"])
def get_transaction_receipt():
    """
    Returns the transaction receipt identified by the transactionHash argument in the GET request.
    """

    transaction_hash = request.args.get("transactionHash")
    ret = starknet_wrapper.get_transaction_receipt(transaction_hash)
    return jsonify(ret)

@app.route("/feeder_gateway/get_transaction_trace", methods=["GET"])
def get_transaction_trace():
    """
    Returns the trace of the transaction identified by the transactionHash argument in the GET request.
    """

    transaction_hash = request.args.get("transactionHash")

    try:
        transaction_trace = starknet_wrapper.get_transaction_trace(transaction_hash)
    except StarkException as err:
        abort(Response(err, 500))

    return jsonify(transaction_trace)

@app.route("/feeder_gateway/get_state_update", methods=["GET"])
def get_state_update():
    """
    Returns the status update from the block identified by the blockHash argument in the GET request.
    If no block hash was provided it will default to the last block.
    """

    block_hash = request.args.get("blockHash")
    block_number = request.args.get("blockNumber", type=custom_int)

    try:
        state_update = starknet_wrapper.get_state_update(block_hash=block_hash, block_number=block_number)
    except StarkException as err:
        abort(Response(err.message, 500))

    return jsonify(state_update)

@app.route("/feeder_gateway/estimate_fee", methods=["POST"])
async def estimate_fee():
    """Currently a dummy implementation, always returning 0."""
    transaction = validate_transaction(request.data, InvokeFunction)
    try:
        actual_fee = await starknet_wrapper.calculate_actual_fee(transaction)
    except StarkException as stark_exception:
        abort(Response(stark_exception.message, 500))

    return jsonify({
        "amount": actual_fee,
        "unit": "wei"
    })

@app.route("/postman/load_l1_messaging_contract", methods=["POST"])
async def load_l1_messaging_contract():
    """
    Loads a MockStarknetMessaging contract. If one is already deployed in the L1 network specified by the networkUrl argument,
    in the address specified in the address argument in the POST body, it is used, otherwise a new one will be deployed.
    The networkId argument is used to check if a local testnet instance or a public testnet should be used.
    """

    request_dict = json.loads(request.data.decode("utf-8"))
    network_url = validate_load_messaging_contract(request_dict)
    contract_address = request_dict.get("address")
    network_id = request_dict.get("networkId")

    result_dict = await starknet_wrapper.load_messaging_contract_in_l1(network_url, contract_address, network_id)
    return jsonify(result_dict)

@app.route("/postman/flush", methods=["POST"])
async def flush():
    """
    Handles all pending L1 <> L2 messages and sends them to the other layer
    """

    result_dict= await starknet_wrapper.postman_flush()
    return jsonify(result_dict)

def validate_load_messaging_contract(request_dict: dict):
    """Ensure `data` is valid Starknet function call. Returns an `InvokeFunction`."""

    network_url = request_dict.get("networkUrl")
    if network_url is None:
        error_message = "L1 network or StarknetMessaging contract address not specified"
        abort(Response(error_message, 400))
    return network_url

@app.route("/dump", methods=["POST"])
def dump():
    """Dumps the starknet_wrapper"""

    request_dict = request.json or {}
    dump_path = request_dict.get("path") or dumper.dump_path
    if not dump_path:
        abort(Response("No path provided", 400))

    dumper.dump(dump_path)
    return Response(status=200)

def dump_on_exit(_signum, _frame):
    """Dumps on exit."""
    dumper.dump(dumper.dump_path)
    sys.exit(0)

starknet_wrapper = StarknetWrapper()
dumper = Dumper(starknet_wrapper)

def main():
    """Runs the server."""

    # pylint: disable=global-statement, invalid-name
    global starknet_wrapper

    # reduce startup logging
    os.environ["WERKZEUG_RUN_MAIN"] = "true"

    args = parse_args()

    # Uncomment this once fork support is added
    # origin = Origin(args.fork) if args.fork else NullOrigin()
    # starknet_wrapper.origin = origin

    if args.load_path:
        try:
            starknet_wrapper = StarknetWrapper.load(args.load_path)
        except (FileNotFoundError, pickle.UnpicklingError):
            sys.exit(f"Error: Cannot load from {args.load_path}. Make sure the file exists and contains a Devnet dump.")

    if args.dump_on == DumpOn.EXIT:
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, dump_on_exit)

    dumper.dump_path = args.dump_path
    dumper.dump_on = args.dump_on

    app.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
