#!/bin/bash

trap 'kill $(jobs -p)' EXIT

host=localhost
port=5000
poetry run starknet-devnet --host="$host" --port="$port" &

GATEWAY_URL="http://$host:$port"
FEEDER_GATEWAY_URL="http://$host:$port"

cd starknet-hardhat-example
npx hardhat starknet-compile --starknet-network starknetLocalhost
npx hardhat starknet-deploy --starknet-network starknetLocalhost
npx hardhat test
