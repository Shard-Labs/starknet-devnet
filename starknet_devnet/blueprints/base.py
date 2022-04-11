"""
Base routes
"""
from flask import Blueprint, abort, Response, request

from starknet_devnet.state import state

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
        abort(Response("No path provided", 400))

    state.dumper.dump(dump_path)
    return Response(status=200)
