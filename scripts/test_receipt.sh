#!/bin/bash

set -e

source scripts/settings.ini
[ -f .env ] && source .env

USAGE="$0: <BLOCK_NUMBER> <TX_HASH>"

if [ "$#" -ne 2 ]; then
    echo "$USAGE"
    exit 1
fi

BLOCK_NUMBER="$1"
TX_HASH="$2"

RECEIPT_FILE=receipt.json
starknet get_transaction_receipt --hash "$TX_HASH" --feeder_gateway_url "$FEEDER_GATEWAY_URL" > "$RECEIPT_FILE"

props_not_found=""
for prop in block_hash block_number execution_resources l2_to_l1_messages status transaction_hash transaction_index; do
    jq --exit-status ".$prop" "$RECEIPT_FILE" 2>&1 > /dev/null  || props_not_found="$props_not_found $prop"
done

if [ -n "$props_not_found" ]; then
    echo "Receipt props not found:$props_not_found"
    exit 1
fi

function compare_json() {
    prop="$1"
    expected_value="$2"
    actual_value=$(jq ".$prop" "$RECEIPT_FILE")
    if [ "$actual_value" = "$expected_value" ]; then
        echo "Correct $prop"
    else
        echo "Incorrect $prop"
        echo "Expected: $expected_value"
        echo "Actual: $actual_value"
        exit 2
    fi
}

compare_json block_number "$BLOCK_NUMBER"
compare_json transaction_hash "\"$TX_HASH\""
compare_json transaction_index 0
