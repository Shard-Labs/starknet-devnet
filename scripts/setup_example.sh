#!/bin/bash
set -e

echo "Installing starknet-hardhat-plugin from source"
git clone -b master --single-branch git@github.com:Shard-Labs/starknet-hardhat-plugin.git
cd starknet-hardhat-plugin
npm ci
npm run build
npm link
cd ..

echo "Cloning starknet-hardhat-example branch 'devnet'"
git clone -b devnet --single-branch git@github.com:Shard-Labs/starknet-hardhat-example.git
cd starknet-hardhat-example
npm ci
npm link @shardlabs/starknet-hardhat-plugin

# generate artifacts
npx hardhat starknet-compile

npx hardhat compile