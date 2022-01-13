#!/bin/bash
set -e

source scripts/settings.ini
[ -f .env ] && source .env

USAGE="$0 <TX_HASH> <EXPECTED_STATUS>"

tx_hash="$1"
if [ -z "$tx_hash" ]; then
    echo "No tx_hash provided"
    echo "$USAGE"
    exit 1
fi

expected_status="$2"
if [ -z "$expected_status" ]; then
    echo "No expected_status provided"
    echo "$USAGE"
    exit 1
fi

if [ -z "$FEEDER_GATEWAY_URL" ]; then
    echo "Environment variable FEEDER_GATEWAY_URL is not defined"
    echo "$USAGE"
    exit 1
fi

received_tx_status=$(starknet tx_status --hash $tx_hash --feeder_gateway_url $FEEDER_GATEWAY_URL | jq ".tx_status" -r)
if [ "$received_tx_status" != "$expected_status" ]; then
    echo "Wrong tx_status: $received_tx_status"
    echo "Expected tx_status: $expected_status"
    exit 2
fi
