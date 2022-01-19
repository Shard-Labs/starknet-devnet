"""
The main testing script. Runs the devnet and calls its endpoints.
"""

from .util import (
    assert_negative_block_input,
    run_devnet_in_background,
    assert_block, assert_contract_code, assert_equal, assert_failing_deploy, assert_receipt, assert_salty_deploy,
    assert_storage, assert_transaction, assert_tx_status,
    call, deploy, invoke
)

ARTIFACTS_PATH = "starknet-hardhat-example/starknet-artifacts/contracts"
CONTRACT_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract.json"
ABI_PATH = f"{ARTIFACTS_PATH}/contract.cairo/contract_abi.json"
FAILING_CONTRACT_PATH = f"{ARTIFACTS_PATH}/always_fail.cairo/always_fail.json"

run_devnet_in_background(sleep_seconds=1)
deploy_info = deploy(CONTRACT_PATH, ["0"])
print("Deployment:", deploy_info)

assert_tx_status(deploy_info["tx_hash"], "ACCEPTED_ON_L2")
assert_transaction(deploy_info["tx_hash"], "ACCEPTED_ON_L2")

# check storage after deployment
BALANCE_KEY = "916907772491729262376534102982219947830828984996257231353398618781993312401"
assert_storage(deploy_info["address"], BALANCE_KEY, "0x0")

# check block and receipt after deployment
assert_negative_block_input()
assert_block(0, deploy_info["tx_hash"])
assert_receipt(0, deploy_info["tx_hash"])

# check code
assert_contract_code(deploy_info["address"], "test/code.expected.json")

# increase and assert balance
invoke_tx_hash = invoke(
    function="increase_balance",
    address=deploy_info["address"],
    abi_path=ABI_PATH,
    inputs=["10", "20"]
)
value = call(
    function="get_balance",
    address=deploy_info["address"],
    abi_path=ABI_PATH
)
assert_equal(value, "30", "Invoke+call failed!")

# check storage, block and receipt after increase
assert_storage(deploy_info["address"], BALANCE_KEY, "0x1e")
assert_block(1, invoke_tx_hash)
assert_receipt(1, invoke_tx_hash)

assert_salty_deploy(
    contract_path=CONTRACT_PATH,
    inputs=["10"],
    salt="0x99",
    expected_address="0x06a9555c51c45990d479a0322c0e438c465a988151423049645773162dd7b1c9",
    expected_tx_hash="0x02d3c5827c7067c485e14943c8893f52873680d72f88396a5d02ddb743dc4598"
)

assert_failing_deploy(
    contract_path=FAILING_CONTRACT_PATH,
)
