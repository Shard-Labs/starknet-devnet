#!/bin/bash
set -e

source scripts/settings.ini
[ -f .env ] && source .env

trap 'kill $(jobs -p)' EXIT

poetry run starknet-devnet --host="$host" --port="$port" &
sleep 1 # give the server some time to get up

CONTRACT_PATH=starknet-hardhat-example/starknet-artifacts/contracts/auth_contract.cairo/auth_contract.json
ABI_PATH=starknet-hardhat-example/starknet-artifacts/contracts/auth_contract.cairo/auth_contract_abi.json

#private_key=12345
public_key=1628448741648245036800002906075225705100596136133912895015035902954123957052
initial_balance=1000
output=$(starknet deploy \
    --contract $CONTRACT_PATH \
    --inputs $public_key $initial_balance \
    --gateway_url $GATEWAY_URL
)
deploy_tx_hash=$(echo "$output" | sed -rn "s/.*Transaction hash: (\w*).*/\1/p")
address=$(echo "$output" | sed -rn "s/.*Contract address: (\w*).*/\1/p")
echo "Address: $address"
echo "tx_hash: $deploy_tx_hash"

# inspects status from tx_status object
deploy_tx_status=$(starknet tx_status --hash $deploy_tx_hash --feeder_gateway_url $FEEDER_GATEWAY_URL | jq ".tx_status" -r)
if [ "$deploy_tx_status" != "ACCEPTED_ON_L2" ]; then
    echo "Wrong tx_status: $deploy_tx_status"
    exit 2
fi

# inspects status from tx object
deploy_tx_status2=$(starknet get_transaction --hash $deploy_tx_hash --feeder_gateway_url $FEEDER_GATEWAY_URL | jq ".status" -r)
if [ "$deploy_tx_status2" != "ACCEPTED_ON_L2" ]; then
    echo "Wrong status in tx: $deploy_tx_status2"
    exit 2
fi

# increase and get balance
input_value=4321
starknet invoke \
    --function increase_balance \
    --inputs $public_key $input_value \
    --signature \
        1225578735933442828068102633747590437426782890965066746429241472187377583468 \
        3568809569741913715045370357918125425757114920266578211811626257903121825123 \
    --address $address \
    --abi $ABI_PATH \
    --gateway_url $GATEWAY_URL

result=$(starknet call \
    --function get_balance \
    --address $address \
    --abi $ABI_PATH \
    --feeder_gateway_url $FEEDER_GATEWAY_URL \
    --inputs $public_key
)

expected=5321
if [ "$result" == "$expected" ]; then
    echo "Invoke successful!"
else
    echo "Invoke failed!"
    echo "Expected: $expected"
    echo "Received: $result"
    exit 2
fi

# check storage
balance_key=142452623821144136554572927896792266630776240502820879601186867231282346767
scripts/test_storage.sh "$address" "$balance_key" 0x14c9
