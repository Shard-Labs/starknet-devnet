#!/bin/bash

set -e

source scripts/settings.ini
[ -f .env ] && source .env

USAGE="$0: <CONTRACT_ADDRESS>"

if [ "$#" -ne 1 ]; then
    echo "$USAGE"
    exit 1
fi

CONTRACT_ADDRESS="$1"

code_result_file=$(mktemp)
CODE_EXPECTED_FILE=scripts/code.expected.json
starknet get_code --contract_address "$CONTRACT_ADDRESS" --feeder_gateway_url="$FEEDER_GATEWAY_URL" > "$code_result_file"
diff "$code_result_file" "$CODE_EXPECTED_FILE"
rm "$code_result_file"
