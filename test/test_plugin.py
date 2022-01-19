"""Script for testing how Devnet interacts with `starknet-harhdat-plugin`."""

import os
import sys
from .util import assert_equal, call, extract_address, my_run, run_devnet_in_background

run_devnet_in_background(sleep_seconds=1)

os.chdir("starknet-hardhat-example")
os.rename(os.environ["HARDHAT_CONFIG_FILE"], "hardhat.config.ts")
# npx hardhat starknet-compile <- Already executed in setup_example.sh

# devnet already defined in config as localhost:5000
deploy_output = my_run([
    "npx", "hardhat", "starknet-deploy",
    "starknet-artifacts/contracts/contract.cairo",
    "--starknet-network", "devnet",
    "--inputs", "10"
], add_gateway_urls=False).stdout
address = extract_address(deploy_output)

balance = call(
    abi_path="starknet-artifacts/contracts/contract.cairo/contract_abi.json",
    address=address,
    function="get_balance"
)
assert_equal(balance, "10")
print("Finished deploy-call procedure")

if os.path.isfile(os.environ["TEST_FILE"]):
    print("Invalid TEST_FILE provided")
    sys.exit(1)

my_run([
    "npx", "hardhat", "test", os.environ["TEST_FILE"]
], add_gateway_urls=False)
