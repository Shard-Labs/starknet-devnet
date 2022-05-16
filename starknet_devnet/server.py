"""
A server exposing Starknet functionalities as API endpoints.
"""

import sys
import meinheld
import dill as pickle

from flask import Flask
from flask_cors import CORS

from starkware.starkware_utils.error_handling import StarkException
from .blueprints.base import base
from .blueprints.gateway import gateway
from .blueprints.feeder_gateway import feeder_gateway
from .blueprints.postman import postman
from .util import DumpOn, parse_args
from .state import state
from .starknet_wrapper import DevnetConfig

app = Flask(__name__)
CORS(app)

@app.before_first_request
async def initialize_starknet():
    """Initialize Starknet to assert it's defined before its first use."""
    await state.starknet_wrapper.initialize()

app.register_blueprint(base)
app.register_blueprint(gateway)
app.register_blueprint(feeder_gateway)
app.register_blueprint(postman)

def handle_accounts(args):
    """Generate accounts """
    if args.accounts:
        state.generate_accounts(
            n_accounts=args.accounts,
            initial_balance=args.initial_balance,
            seed=args.seed
        )

def handle_dump(args):
    """Assign dumping options from args to state."""
    state.dumper.dump_path = args.dump_path
    state.dumper.dump_on = args.dump_on

def handle_load(args):
    """Load state if specified."""
    if args.load_path:
        try:
            state.load(args.load_path)
        except (FileNotFoundError, pickle.UnpicklingError):
            sys.exit(f"Error: Cannot load from {args.load_path}. Make sure the file exists and contains a Devnet dump.")

def handle_lite_mode(args):
    """Enable lite mode if specified."""
    if args.lite_mode:
        config = DevnetConfig(
            lite_mode_block_hash=True,
            lite_mode_deploy_hash=True
        )
    else:
        config = DevnetConfig(
            lite_mode_block_hash=args.lite_mode_block_hash,
            lite_mode_deploy_hash=args.lite_mode_deploy_hash
        )

    state.starknet_wrapper.set_config(config)

def handle_start_time(args):
    """Assign start time if specified."""
    if args.start_time is not None:
        state.starknet_wrapper.set_block_time(args.start_time)

def main():
    """Runs the server."""

    args = parse_args()

    # Uncomment this once fork support is added
    # origin = Origin(args.fork) if args.fork else NullOrigin()
    # starknet_wrapper.origin = origin

    handle_accounts(args)
    handle_load(args)
    handle_dump(args)
    handle_lite_mode(args)
    handle_start_time(args)

    try:
        meinheld.listen((args.host, args.port))
        print(f" * Listening on http://{args.host}:{args.port}/ (Press CTRL+C to quit)")
        meinheld.run(app)
    except KeyboardInterrupt:
        pass
    finally:
        if args.dump_on == DumpOn.EXIT:
            state.dumper.dump()
            sys.exit(0)

@app.errorhandler(StarkException)
def handle(error: StarkException):
    """Handles the error and responds in JSON. """
    return {"message": error.message, "status_code": error.status_code}, error.status_code

if __name__ == "__main__":
    main()
