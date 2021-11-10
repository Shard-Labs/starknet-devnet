#!/bin/bash
set -e

[ -f .env ] && source .env

trap 'kill $(jobs -p)' EXIT

host=localhost
port=5000
poetry run starknet-devnet --host="$host" --port="$port" &
sleep 1 # give the server some time to get up

GATEWAY_URL="http://$host:$port"
FEEDER_GATEWAY_URL="http://$host:$port"

CONTRACT_PATH=starknet-hardhat-example/starknet-artifacts/contracts/contract.cairo/contract.json
ABI_PATH=starknet-hardhat-example/starknet-artifacts/contracts/contract.cairo/contract_abi.json

output=$(starknet deploy --contract $CONTRACT_PATH --gateway_url=$GATEWAY_URL)
deploy_tx_hash=$(echo $output | sed -r "s/.*Transaction hash: (\w*).*/\1/")
address=$(echo $output | sed -r "s/.*Contract address: (\w*).*/\1/")
echo "Address: $address"
echo "tx_hash: $deploy_tx_hash"

# inspects status from tx_status object
deploy_tx_status=$(starknet tx_status --hash $deploy_tx_hash --feeder_gateway_url $FEEDER_GATEWAY_URL | jq ".tx_status" -r)
if [ "$deploy_tx_status" != "PENDING" ]; then
    echo "Wrong tx_status: $deploy_tx_status"
    exit 2
fi

# inspects status from tx object
deploy_tx_status2=$(starknet get_transaction --hash $deploy_tx_hash --feeder_gateway_url $FEEDER_GATEWAY_URL | jq ".status" -r)
if [ "$deploy_tx_status2" != "PENDING" ]; then
    echo "Wrong status in tx: $deploy_tx_status2"
    exit 2
fi

starknet invoke --function increase_balance --inputs 10 20 --address $address --abi $ABI_PATH --gateway_url=$GATEWAY_URL
result=$(starknet call --function get_balance --address $address --abi $ABI_PATH --feeder_gateway_url=$FEEDER_GATEWAY_URL)

expected=30
echo
if [ "$result" == "$expected" ]; then
    echo "Success!"
else
    echo "Test failed!"
    echo "Expected: $expected"
    echo "Received: $result"
    exit 2
fi
