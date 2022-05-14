"""
Base routes
"""
from flask import Blueprint, Response, request, jsonify

from starknet_devnet.state import state
from starknet_devnet.util import StarknetDevnetException

base = Blueprint("base", __name__)

@base.route("/is_alive", methods=["GET"])
def is_alive():
    """Health check endpoint."""
    return "Alive!!!"

@base.route("/restart", methods=["POST"])
def restart():
    """Restart the starknet_wrapper"""
    state.reset()
    return Response(status=200)

@base.route("/dump", methods=["POST"])
def dump():
    """Dumps the starknet_wrapper"""

    request_dict = request.json or {}
    dump_path = request_dict.get("path") or state.dumper.dump_path
    if not dump_path:
        raise StarknetDevnetException(message="No path provided.", status_code=400)

    state.dumper.dump(dump_path)
    return Response(status=200)

def validate_time_value(value: int):
    """Validates the time value"""
    if value is None:
        raise StarknetDevnetException(message="Time value must be provided.", status_code=400)

    if not isinstance(value, int):
        raise StarknetDevnetException(message="Time value must be an integer.", status_code=400)

    if value < 0:
        raise StarknetDevnetException(message="Time value must be greater than 0.", status_code=400)


@base.route("/increase_time", methods=["POST"])
def increase_time():
    """Increases the block timestamp offset"""
    request_dict = request.json or {}
    time_s = request_dict.get("time")
    validate_time_value(time_s)

    state.starknet_wrapper.increase_block_time(time_s)

    return jsonify({"timestamp_increased_by": time_s})

@base.route("/set_time", methods=["POST"])
def set_time():
    """Sets the block timestamp offset"""
    request_dict = request.json or {}
    time_s = request_dict.get("time")
    validate_time_value(time_s)

    state.starknet_wrapper.set_block_time(time_s)

    return jsonify({"next_block_timestamp": time_s})
