from flask import Flask, request, jsonify, abort
from flask.wrappers import Response
from flask_cors import CORS
from starkware.starknet.services.api.gateway.transaction import Deploy, InvokeFunction, Transaction
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.error_handling import StarkErrorCode, StarkException
from .util import TxStatus, parse_args
from .starknet_wrapper import Choice, StarknetWrapper

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
    transaction = Transaction.loads(raw_data)

    tx_type = transaction.tx_type.name
    result_dict = {}

    if tx_type == TransactionType.DEPLOY.name:
        deploy_transaction: Deploy = transaction

        contract_address = await starknet_wrapper.deploy(
            contract_definition=deploy_transaction.contract_definition,
            constructor_calldata=deploy_transaction.constructor_calldata
        )
        transaction_hash = starknet_wrapper.store_deploy_transaction(
            contract_address=contract_address,
            constructor_calldata=deploy_transaction.constructor_calldata
        )

    elif tx_type == TransactionType.INVOKE_FUNCTION.name:
        transaction: InvokeFunction = transaction
        contract_address = hex(transaction.contract_address)
        status = TxStatus.PENDING
        error_message = None
        try:
            result_dict = await starknet_wrapper.call_or_invoke(
                Choice.INVOKE,
                contract_address=transaction.contract_address,
                entry_point_selector=transaction.entry_point_selector,
                calldata=transaction.calldata,
                signature=transaction.signature
            )
        except StarkException as e:
            error_message = e.message
            status = TxStatus.REJECTED

        transaction_hash = starknet_wrapper.store_invoke_transaction(
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

def main():
    args = parse_args()
    app.run(**vars(args))

if __name__ == "__main__":
    main()
