"""
A server exposing Starknet functionalities as API endpoints.
"""

import os

from flask import Flask, request, jsonify, abort
from flask.wrappers import Response
from flask_cors import CORS
from marshmallow import ValidationError
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Transaction
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.error_handling import StarkErrorCode, StarkException
from werkzeug.datastructures import MultiDict

from .constants import CAIRO_LANG_VERSION
from .starknet_wrapper import StarknetWrapper
from .util import custom_int, fixed_length_hex, parse_args

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
        contract_address, transaction_hash, result_dict = await starknet_wrapper.invoke(transaction)
    else:
        abort(Response(f"Invalid tx_type: {tx_type}.", 400))

    return jsonify({
        "code": StarkErrorCode.TRANSACTION_RECEIVED.name,
        "transaction_hash": fixed_length_hex(transaction_hash),
        "address": fixed_length_hex(contract_address),
        **result_dict
    })

def validate_transaction(data: bytes):
    """Ensure `data` is a valid Starknet transaction. Returns the parsed `Transaction`."""

    try:
        transaction = Transaction.loads(data)
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

@app.route("/feeder_gateway/get_block", methods=["GET"])
async def get_block():
    """Endpoint for retrieving a block identified by its hash or number."""

    block_hash = request.args.get("blockHash")
    block_number = request.args.get("blockNumber", type=custom_int)

    if block_hash is not None and block_number is not None:
        message = "Ambiguous criteria: only one of (block number, block hash) can be provided."
        abort(Response(message, 500))

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

starknet_wrapper = StarknetWrapper()

def main():
    """Runs the server."""

    # reduce startup logging
    os.environ["WERKZEUG_RUN_MAIN"] = "true"

    args = parse_args()
    # Uncomment this once fork support is added
    # origin = Origin(args.fork) if args.fork else NullOrigin()
    # starknet_wrapper.set_origin(origin)

    app.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
