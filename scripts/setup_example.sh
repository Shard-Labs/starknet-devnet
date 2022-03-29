#!/bin/bash
set -e

echo "Cloning starknet-hardhat-example branch 'devnet'"
git clone -b devnet --single-branch git@github.com:Shard-Labs/starknet-hardhat-example.git
cd starknet-hardhat-example
npm ci

# generate artifacts
npx hardhat starknet-compile
npx hardhat compile
