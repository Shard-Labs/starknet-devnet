#!/bin/bash
set -e

trap 'kill $(jobs -p)' EXIT

poetry run starknet-devnet --host=localhost --port=5000 &
GATEWAY_URL=http://localhost:5000
sleep 1 # give the server some time to get up

function extract_address () {
    sed -nr "s/^Contract address: (.*)$/\1/p"
}

function call_wrapper() {
    read ADDRESS
    starknet call \
        --abi starknet-artifacts/contracts/contract.cairo/contract_abi.json \
        --address $ADDRESS \
        --feeder_gateway_url $GATEWAY_URL \
        --func get_balance
}

function result_assertion() {
    read RES
    if [ "$RES" != "10" ]; then
        echo "Wrong result: $RES"
        exit 1
    fi
}

cd starknet-hardhat-example
# npx hardhat starknet-compile <- Already executed in setup-example.sh
# devnet already defined in config as localhost:5000
npx hardhat starknet-deploy \
    starknet-artifacts/contracts/contract.cairo \
    --starknet-network devnet \
    --inputs 10 \
| extract_address \
| call_wrapper \
| result_assertion
echo "Finished deploy-call procedure"

npx hardhat test
