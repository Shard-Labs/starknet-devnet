#!/bin/bash

TEST_DIRECTORY=test/contracts
ARTIFACTS_DIRECTORY=test/artifacts

# delete all artifacts
rm -rf $ARTIFACTS_DIRECTORY

# create artifacts directory
mkdir -p $ARTIFACTS_DIRECTORY

# compile Solidity test contracts first
# order matters as Hardhat will remove Cairo artifacts
echo "Compiling Solidity contracts with Hardhat $(npx hardhat --version)"
npx hardhat compile

# compile Cairo test contracts
echo "Compiling Cairo contracts with $(poetry run starknet-compile --version)"

NUMBER_OF_CONTRACTS=0
for contract in "$TEST_DIRECTORY"/cairo/*.cairo; do

    # create contract directory
    directory=$ARTIFACTS_DIRECTORY/contracts/cairo/"${contract##*/}"
    mkdir -p "$directory"


    basename=$(basename "$contract")
    output=$directory/"${basename%.*}.json"
    abi=$directory/"${basename%.*}_abi.json"

    poetry run starknet-compile --output "$output" --abi "$abi" "$contract"
    NUMBER_OF_CONTRACTS=$((NUMBER_OF_CONTRACTS+1))
done

echo "Compiled $NUMBER_OF_CONTRACTS Cairo files successfully"