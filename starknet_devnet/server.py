from flask import Flask, request, jsonify, abort
from flask.wrappers import Response
from flask_cors import CORS
from starkware.starknet.business_logic.internal_transaction import InternalDeploy
from starkware.starknet.services.api.gateway.transaction import InvokeFunction, Transaction
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.error_handling import StarkErrorCode, StarkException
from werkzeug.datastructures import MultiDict
from .util import TxStatus, custom_int, fixed_length_hex, parse_args
from .starknet_wrapper import Choice, StarknetWrapper
import os

app = Flask(__name__)
CORS(app)

starknet_wrapper = StarknetWrapper()

@app.route("/is_alive", methods=["GET"])
@app.route("/gateway/is_alive", methods=["GET"])
@app.route("/feeder_gateway/is_alive", methods=["GET"])
def is_alive():
    return "Alive!!!"

@app.route("/gateway/add_transaction", methods=["POST"])
async def add_transaction():
    """
    Endpoint for accepting DEPLOY and INVOKE_FUNCTION transactions.
    """

    raw_data = request.get_data()
    try:
        transaction = Transaction.loads(raw_data)
    except TypeError:
        msg = "Invalid transaction format. Try recompiling your contract with a newer version."
        abort(Response(msg, 400))

    tx_type = transaction.tx_type.name
    result_dict = {}
    status = TxStatus.ACCEPTED_ON_L2
    error_message = None

    if tx_type == TransactionType.DEPLOY.name:
        state = await starknet_wrapper.get_state()
        deploy_transaction: InternalDeploy = InternalDeploy.from_external(transaction, state.general_config)
        contract_address = deploy_transaction.contract_address
        try:
            await starknet_wrapper.deploy(
                contract_definition=deploy_transaction.contract_definition,
                contract_address_salt=deploy_transaction.contract_address_salt,
                constructor_calldata=deploy_transaction.constructor_calldata
            )
        except StarkException as e:
            error_message = e.message
            status = TxStatus.REJECTED

        transaction_hash = await starknet_wrapper.store_deploy_transaction(
            contract_address=contract_address,
            calldata=deploy_transaction.constructor_calldata,
            salt=deploy_transaction.contract_address_salt,
            status=status,
            error_message=error_message
        )

    elif tx_type == TransactionType.INVOKE_FUNCTION.name:
        transaction: InvokeFunction = transaction
        contract_address = transaction.contract_address
        try:
            result_dict = await starknet_wrapper.call_or_invoke(
                Choice.INVOKE,
                contract_address=contract_address,
                entry_point_selector=transaction.entry_point_selector,
                calldata=transaction.calldata,
                signature=transaction.signature
            )
        except StarkException as e:
            error_message = e.message
            status = TxStatus.REJECTED

        transaction_hash = await starknet_wrapper.store_invoke_transaction(
            contract_address=contract_address,
            calldata=transaction.calldata,
            entry_point_selector=transaction.entry_point_selector,
            status=status,
            error_message=error_message
        )

    else:
        abort(Response(f"Invalid tx_type: {tx_type}.", 400))

    return jsonify({
        "code": StarkErrorCode.TRANSACTION_RECEIVED.name,
        "transaction_hash": transaction_hash,
        "address": fixed_length_hex(contract_address),
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
    try:
        result_dict = await starknet_wrapper.call_or_invoke(
            Choice.CALL,
            contract_address=call_specifications.contract_address,
            entry_point_selector=call_specifications.entry_point_selector,
            calldata=call_specifications.calldata,
            signature=call_specifications.signature
        )
    except StarkException as e:
        # code 400 would make more sense, but alpha returns 500
        abort(Response(e.message, 500))

    return jsonify(result_dict)

def check_block_hash(request_args: MultiDict):
    block_hash = request_args.get("blockHash", type=custom_int)
    if block_hash is not None:
        print("Specifying a block by its hash is not supported. All interaction is done with the latest block.")

@app.route("/feeder_gateway/get_block", methods=["GET"])
async def get_block():
    block_hash = request.args.get("blockHash")
    block_number = request.args.get("blockNumber", type=custom_int)
    try:
        result_dict = starknet_wrapper.get_block(block_hash=block_hash, block_number=block_number)
    except StarkException as e:
        abort(Response(e.message, 500))
    return jsonify(result_dict)

@app.route("/feeder_gateway/get_code", methods=["GET"])
def get_code():
    """
    Returns the ABI and bytecode of the contract whose contractAddress is provided.
    """
    check_block_hash(request.args)

    contract_address = request.args.get("contractAddress", type=custom_int)
    result_dict = starknet_wrapper.get_code(contract_address)
    return jsonify(result_dict)

@app.route("/feeder_gateway/get_storage_at", methods=["GET"])
async def get_storage_at():
    check_block_hash(request.args)

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

    return "Not implemented", 501

def main():
    # reduce startup logging
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'

    args = parse_args()
    app.run(**vars(args))

if __name__ == "__main__":
    main()
