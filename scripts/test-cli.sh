#!/bin/bash
set -e

source scripts/settings.ini
[ -f .env ] && source .env

trap 'kill $(jobs -p)' EXIT

poetry run starknet-devnet --host="$host" --port="$port" &
sleep 1 # give the server some time to get up

CONTRACT_PATH=starknet-hardhat-example/starknet-artifacts/contracts/contract.cairo/contract.json
ABI_PATH=starknet-hardhat-example/starknet-artifacts/contracts/contract.cairo/contract_abi.json

# deploy the contract
output=$(starknet deploy \
    --contract $CONTRACT_PATH \
    --inputs 0 \
    --gateway_url $GATEWAY_URL
)
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

# check storage after deployment
balance_key=916907772491729262376534102982219947830828984996257231353398618781993312401
scripts/test-storage.sh "$address" "$balance_key" 0x0

# check code
code_result_file=$(mktemp)
code_expected_file=scripts/code.expected.json
starknet get_code --contract_address $address --feeder_gateway_url=$FEEDER_GATEWAY_URL > "$code_result_file"
diff "$code_result_file" "$code_expected_file"
rm "$code_result_file"

# increase and get balance
starknet invoke --function increase_balance --inputs 10 20 --address $address --abi $ABI_PATH --gateway_url=$GATEWAY_URL
result=$(starknet call --function get_balance --address $address --abi $ABI_PATH --feeder_gateway_url=$FEEDER_GATEWAY_URL)

expected=30
echo
if [ "$result" == "$expected" ]; then
    echo "Invoke successful!"
else
    echo "Invoke failed!"
    echo "Expected: $expected"
    echo "Received: $result"
    exit 2
fi

# check storage after increase
scripts/test-storage.sh "$address" "$balance_key" 0x1e
