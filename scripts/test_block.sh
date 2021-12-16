#!/bin/bash

set -e

source scripts/settings.ini
[ -f .env ] && source .env

USAGE="$0: <LATEST_BLOCK> <LATEST_TX_HASH>"

if [ "$#" -ne 2 ]; then
    echo "$USAGE"
    exit 1
fi

LATEST_BLOCK="$1"
LATEST_TX_HASH="$2"

function custom_get_block() {
    number="$1"
    if [ -n "$number" ]; then
        starknet get_block --feeder_gateway_url "$FEEDER_GATEWAY_URL" --number "$number"
    else
        starknet get_block --feeder_gateway_url "$FEEDER_GATEWAY_URL"
    fi
}

custom_get_block -1 2>&1 && echo "Should fail" && exit 2 || echo "Correctly rejecting negative input"

# try too big block number
# this tests behavior in case of bad input and retrieves number of blocks
TOO_BIG=1000
total_blocks=$(
    custom_get_block "$TOO_BIG" 2>&1 |
    sed -rn "s/^.*There are currently (.*) blocks.*$/\1/p"
)
extracted_latest_block=$((total_blocks - 1))

if [ "$LATEST_BLOCK" != "$extracted_latest_block" ]; then
    echo "Expected and extracted latest block are different"
    echo "Expected: $LATEST_BLOCK"
    echo "Extracted: $extracted_latest_block"
    exit 2
fi

latest_block_file=$(mktemp)
custom_get_block > "$latest_block_file"
specific_block_file=$(mktemp)
custom_get_block "$LATEST_BLOCK" > "$specific_block_file"
diff "$latest_block_file" "$specific_block_file"

extracted_block_number=$(jq -r ".block_number" "$latest_block_file")
[ "$extracted_block_number" != "$LATEST_BLOCK" ] &&
    echo "Wrong block_number in block: $extracted_block_number; expected: $LATEST_BLOCK" && exit 2

extracted_status=$(jq -r ".status" "$latest_block_file")
[ "$extracted_status" != "ACCEPTED_ON_L2" ] &&
    echo "Wrong status in block: $extracted_status" && exit 2

extracted_tx_hash=$(jq -r ".transactions[0].transaction_hash" "$latest_block_file")
[ "$extracted_tx_hash" != "$LATEST_TX_HASH" ] &&
    echo "Wrong tx_hash in block: $extracted_tx_hash; expected: $LATEST_TX_HASH" && exit 2

rm "$latest_block_file"
rm "$specific_block_file"
