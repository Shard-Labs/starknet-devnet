#!/bin/bash
set -e

source scripts/settings.ini
[ -f .env ] && source .env

function extract_tx_hash() {
    output="$1"
    echo "$output" | sed -rn "s/.*Transaction hash: (\w*).*/\1/p"
}

function deploy_with_salt() {
    salt_output=$(starknet deploy --contract "$CONTRACT_PATH" --salt 0x99 --inputs 10 --gateway_url "$GATEWAY_URL")
    echo "$salt_output" \
        | tail -n +1 \
        | diff - scripts/deploy_expected.txt

    salt_hash=$(extract_tx_hash "$salt_output")
    scripts/assert_tx_status.sh "$salt_hash" "ACCEPTED_ON_L2"
}

# repeat experiment twice to see if the second run fails
echo "Deploying with salt 1)"
deploy_with_salt
echo "Deploying with salt 2)"
deploy_with_salt

failing_output=$(starknet deploy --contract "$FAILING_CONTRACT" --gateway_url "$GATEWAY_URL")
failing_deploy_hash=$(extract_tx_hash "$failing_output")

scripts/assert_tx_status.sh "$failing_deploy_hash" "REJECTED"
