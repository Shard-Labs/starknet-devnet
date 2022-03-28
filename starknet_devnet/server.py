"""
A server exposing Starknet functionalities as API endpoints.
"""

import os
import sys
import meinheld
import dill as pickle

from flask import Flask
from flask_cors import CORS

from .blueprints.base import base
from .blueprints.gateway import gateway
from .blueprints.feeder_gateway import feeder_gateway
from .blueprints.postman import postman
from .util import DumpOn, parse_args
from .state import state

app = Flask(__name__)
CORS(app)

app.register_blueprint(base)
app.register_blueprint(gateway)
app.register_blueprint(feeder_gateway)
app.register_blueprint(postman)

def main():
    """Runs the server."""

    # pylint: disable=global-statement, invalid-name

    # reduce startup logging
    os.environ["WERKZEUG_RUN_MAIN"] = "true"

    args = parse_args()

    # Uncomment this once fork support is added
    # origin = Origin(args.fork) if args.fork else NullOrigin()
    # starknet_wrapper.origin = origin

    if args.load_path:
        try:
            state.load(args.load_path)
        except (FileNotFoundError, pickle.UnpicklingError):
            sys.exit(f"Error: Cannot load from {args.load_path}. Make sure the file exists and contains a Devnet dump.")

    state.dumper.dump_path = args.dump_path
    state.dumper.dump_on = args.dump_on

    if args.lite_mode:
        state.starknet_wrapper.lite_mode_block_hash = True
        state.starknet_wrapper.lite_mode_deploy_hash = True
    else:
        state.starknet_wrapper.lite_mode_block_hash = args.lite_mode_block_hash
        state.starknet_wrapper.lite_mode_deploy_hash = args.lite_mode_deploy_hash

    try:
        meinheld.listen((args.host, args.port))
        meinheld.run(app)
    finally:
        if args.dump_on == DumpOn.EXIT:
            state.dumper.dump()
            sys.exit(0)

if __name__ == "__main__":
    main()
