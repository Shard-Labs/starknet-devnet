#!/bin/bash

set -e

source scripts/settings.ini
[ -f .env ] && source .env

USAGE="$0: <CONTRACT_ADDRESS> <KEY> <EXPECTED>"

if [ "$#" -ne 3 ]; then
    echo "$USAGE"
    exit 1
fi

CONTRACT_ADDRESS="$1"
KEY="$2"
EXPECTED="$3"

result=$(starknet get_storage_at --contract_address "$CONTRACT_ADDRESS" --key "$KEY" --feeder_gateway_url "$FEEDER_GATEWAY_URL")

if [ "$result" == "$EXPECTED" ]; then
    echo "Got storage successfully: $result"
else
    echo "Getting storage failed!"
    echo "Expected: $EXPECTED"
    echo "Received: $result"
    exit 2
fi
