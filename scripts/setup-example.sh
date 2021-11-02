#!/bin/bash
set -e

echo "Cloning branch 'devnet'"
git clone -b devnet --single-branch git@github.com:Shard-Labs/starknet-hardhat-example.git
cd starknet-hardhat-example
npm ci

# describe starknetLocalhost
cp ../scripts/hardhat.config.ts hardhat.config.ts

# generate artifacts
npx hardhat starknet-compile
