#!/bin/bash
set -e

source scripts/settings.ini
[ -f .env ] && source .env

trap 'kill $(jobs -p)' EXIT

function extract_tx_hash() {
    output="$1"
    echo "$output" | sed -rn "s/.*Transaction hash: (\w*).*/\1/p"
}

poetry run starknet-devnet --host="$host" --port="$port" &
sleep 1 # give the server some time to get up

ARTIFACTS_PATH=starknet-hardhat-example/starknet-artifacts/contracts
export CONTRACT_PATH="$ARTIFACTS_PATH/contract.cairo/contract.json"
export ABI_PATH="$ARTIFACTS_PATH/contract.cairo/contract_abi.json"
export FAILING_CONTRACT="$ARTIFACTS_PATH/always_fail.cairo/always_fail.json"

# deploy the contract
output=$(starknet deploy \
    --contract $CONTRACT_PATH \
    --inputs 0 \
    --gateway_url $GATEWAY_URL
)
deploy_tx_hash=$(extract_tx_hash "$output")
address=$(echo "$output" | sed -rn "s/.*Contract address: (\w*).*/\1/p")
echo "Address: $address"
echo "tx_hash: $deploy_tx_hash"

# inspects status from tx_status object
scripts/assert_tx_status.sh "$deploy_tx_hash" "ACCEPTED_ON_L2"

# inspects status from tx object
deploy_tx_status2=$(starknet get_transaction --hash $deploy_tx_hash --feeder_gateway_url $FEEDER_GATEWAY_URL | jq ".status" -r)
if [ "$deploy_tx_status2" != "ACCEPTED_ON_L2" ]; then
    echo "Wrong status in tx: $deploy_tx_status2"
    exit 2
fi

# check storage after deployment
balance_key=916907772491729262376534102982219947830828984996257231353398618781993312401
scripts/test_storage.sh "$address" "$balance_key" 0x0

# check block and receipt after deployment
scripts/test_block.sh 0 "$deploy_tx_hash"
scripts/test_receipt.sh 0 "$deploy_tx_hash"

# check code
scripts/test_code.sh "$address"

# increase and get balance
invoke_output=$(starknet invoke --function increase_balance --inputs 10 20 --address $address --abi "$ABI_PATH" --gateway_url "$GATEWAY_URL")
invoke_tx_hash=$(extract_tx_hash "$invoke_output")
result=$(starknet call --function get_balance --address $address --abi "$ABI_PATH" --feeder_gateway_url "$FEEDER_GATEWAY_URL")

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
scripts/test_storage.sh "$address" "$balance_key" 0x1e

# check block and receipt after increase
scripts/test_block.sh 1 "$invoke_tx_hash"
scripts/test_receipt.sh 1 "$invoke_tx_hash"

# test deployment cases
scripts/test_deploy.sh
