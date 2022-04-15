"""
Gateway routes
"""
from flask import Blueprint, request, jsonify
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starkware_utils.error_handling import StarkErrorCode

from starknet_devnet.util import DumpOn, StarknetDevnetException,fixed_length_hex
from starknet_devnet.state import state
from .shared import validate_transaction

gateway = Blueprint("gateay", __name__, url_prefix="/gateway")

@gateway.route("/is_alive", methods=["GET"])
def is_alive():
    """Health check endpoint."""
    return "Alive!!!"

@gateway.route("/add_transaction", methods=["POST"])
async def add_transaction():
    """Endpoint for accepting DEPLOY and INVOKE_FUNCTION transactions."""

    transaction = validate_transaction(request.data)
    tx_type = transaction.tx_type.name

    if tx_type == TransactionType.DEPLOY.name:
        contract_address, transaction_hash = await state.starknet_wrapper.deploy(transaction)
        result_dict = {}
    elif tx_type == TransactionType.INVOKE_FUNCTION.name:
        contract_address, transaction_hash, result_dict = await state.starknet_wrapper.invoke(transaction)
    else:
        raise StarknetDevnetException(message=f"Invalid tx_type: {tx_type}.", status_code=400)

    # after tx
    if state.dumper.dump_on == DumpOn.TRANSACTION:
        state.dumper.dump()

    return jsonify({
        "code": StarkErrorCode.TRANSACTION_RECEIVED.name,
        "transaction_hash": hex(transaction_hash),
        "address": fixed_length_hex(contract_address),
        **result_dict
    })
