"""
A server exposing Starknet functionalities as API endpoints.
"""

import json
import os
import signal
import sys
import dill as pickle

from flask import Flask, abort, Response, jsonify, request
from flask_cors import CORS

from .blueprints.base import base
from .blueprints.gateway import gateway
from .blueprints.feeder_gateway import feeder_gateway
# from .blueprints.postman import postman
from .util import DumpOn, parse_args
from .state import state

app = Flask(__name__)
CORS(app)

app.register_blueprint(base)
app.register_blueprint(gateway)
app.register_blueprint(feeder_gateway)
# app.register_blueprint(postman)

def validate_load_messaging_contract(request_dict: dict):
    """Ensure `data` is valid Starknet function call. Returns an `InvokeFunction`."""

    network_url = request_dict.get("networkUrl")
    if network_url is None:
        error_message = "L1 network or StarknetMessaging contract address not specified"
        abort(Response(error_message, 400))
    return network_url

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

    result_dict = await state.starknet_wrapper.load_messaging_contract_in_l1(network_url, contract_address, network_id)
    return jsonify(result_dict)

@app.route("/postman/flush", methods=["POST"])
async def flush():
    """
    Handles all pending L1 <> L2 messages and sends them to the other layer
    """

    result_dict= await state.starknet_wrapper.postman_flush()
    return jsonify(result_dict)

def dump_on_exit(_signum, _frame):
    """Dumps on exit."""
    state.dumper.dump(state.dumper.dump_path)
    sys.exit(0)

def main():
    """Runs the server."""

    # pylint: disable=global-statement, invalid-name

    # reduce startup logging
    os.environ["WERKZEUG_RUN_MAIN"] = "true"

    args = parse_args()

    # Uncomment this once fork support is added
    # origin = Origin(args.fork) if args.fork else NullOrigin()
    # starknet_wrapper.set_origin(origin)

    if args.load_path:
        try:
            state.load(args.load_path)
        except (FileNotFoundError, pickle.UnpicklingError):
            sys.exit(f"Error: Cannot load from {args.load_path}. Make sure the file exists and contains a Devnet dump.")

    if args.dump_on == DumpOn.EXIT:
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, dump_on_exit)

    state.dumper.dump_path = args.dump_path
    state.dumper.dump_on = args.dump_on

    app.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
