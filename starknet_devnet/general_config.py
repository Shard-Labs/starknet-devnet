"""
Default general config.
"""

from starkware.starknet.definitions.general_config import (
    build_general_config,
    DEFAULT_CHAIN_ID,
    DEFAULT_FEE_TOKEN_ADDRESS,
    DEFAULT_GAS_PRICE,
    DEFAULT_MAX_STEPS,
    DEFAULT_SEQUENCER_ADDRESS,
)
from starkware.starknet.definitions import constants

DEFAULT_GENERAL_CONFIG = build_general_config({
    "cairo_resource_fee_weights": {
        "n_steps": constants.N_STEPS_FEE_WEIGHT,
    },
    "contract_storage_commitment_tree_height": constants.CONTRACT_STATES_COMMITMENT_TREE_HEIGHT,
    "event_commitment_tree_height": constants.EVENT_COMMITMENT_TREE_HEIGHT,
    "global_state_commitment_tree_height": constants.CONTRACT_ADDRESS_BITS,
    "invoke_tx_max_n_steps": DEFAULT_MAX_STEPS,
    "min_gas_price": DEFAULT_GAS_PRICE,
    "sequencer_address": hex(DEFAULT_SEQUENCER_ADDRESS),
    "starknet_os_config": {
        "chain_id": DEFAULT_CHAIN_ID.name,
        "fee_token_address": hex(DEFAULT_FEE_TOKEN_ADDRESS)
    },
    "tx_version": constants.TRANSACTION_VERSION,
    "tx_commitment_tree_height": constants.TRANSACTION_COMMITMENT_TREE_HEIGHT
})
