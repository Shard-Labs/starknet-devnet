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

if [ -z "$CONTRACT_PATH" ]; then
    echo "No CONTRACT_PATH specified"
    exit 1
fi

if [ -z "$ABI_PATH" ]; then
    echo "No ABI_PATH specified"
    exit 2
fi

output=$(starknet deploy --contract $CONTRACT_PATH --gateway_url=$GATEWAY_URL)
deploy_tx_id=$(echo $output | sed -r "s/.*Transaction ID: (\w*).*/\1/")
address=$(echo $output | sed -r "s/.*Contract address: (\w*).*/\1/")
echo "Address: $address"
echo "tx_id: $deploy_tx_id"
starknet invoke --function increase_balance --inputs 10 20 --address $address --abi $ABI_PATH --gateway_url=$GATEWAY_URL
#starknet tx_status --id $deploy_tx_id
result=$(starknet call --function get_balance --address $address --abi $ABI_PATH --feeder_gateway_url=$FEEDER_GATEWAY_URL)

expected=30
echo
if [ "$result" == "$expected" ]; then
    echo "Success!"
else
    echo "Test failed!"
    echo "Expected: $expected"
    echo "Received: $result"
    exit 1
fi
