"""
Shared functions between blueprints
"""

from flask import abort, Response
from marshmallow import ValidationError
from starkware.starknet.services.api.gateway.transaction import Transaction

from starknet_devnet.constants import CAIRO_LANG_VERSION

def validate_transaction(data: bytes, loader: Transaction=Transaction):
    """Ensure `data` is a valid Starknet transaction. Returns the parsed `Transaction`."""
    try:
        transaction = loader.loads(data)
    except (TypeError, ValidationError) as err:
        msg = f"Invalid tx: {err}\nBe sure to use the correct compilation (json) artifact. Devnet-compatible cairo-lang version: {CAIRO_LANG_VERSION}"
        abort(Response(msg, 400))
    return transaction
