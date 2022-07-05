## Introduction

A Flask wrapper of Starknet state. Similar in purpose to Ganache.

Aims to mimic Starknet's Alpha testnet, but with simplified functionality.

## Contents

- [Install](#install)
- [Disclaimer](#disclaimer)
- [Run](#run)
- [Interaction](#interaction)
- [JSON-RPC API](#json-rpc-api)
- [Dumping and Loading](#dumping)
- [Hardhat Integration](#hardhat-integration)
- [L1-L2 Postman Communication](#postman-integration)
- [Block Explorer](#block-explorer)
- [Lite Mode](#lite-mode)
- [Restart](#restart)
- [Advancing time](#advancing-time)
- [Contract debugging](#contract-debugging)
- [Predeployed accounts](#predeployed-accounts)
- [Devnet speed-up troubleshooting](#devnet-speed-up-troubleshooting)
- [Development](#development)

## Install

```text
pip install starknet-devnet
```

### Requirements

Works with Python versions >=3.7.2 and <3.10.

On Ubuntu/Debian, first run:

```text
sudo apt install -y libgmp3-dev
```

On Mac, you can use `brew`:

```text
brew install gmp
```

## Disclaimer

- Devnet should not be used as a replacement for Alpha testnet. After testing on Devnet, be sure to test on testnet (alpha-goerli)!
- Specifying a block by its hash/number is not supported. All interaction is done with the latest block.
- Sending transactions with max_fee set to 0 is supported (not supported on alpha-mainnet or alpha-goerli).

## Run

Installing the package adds the `starknet-devnet` command.

```text
usage: starknet-devnet [-h] [-v] [--host HOST] [--port PORT]

Run a local instance of Starknet Devnet

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Print the version
  --host HOST           Specify the address to listen at; defaults to
                        127.0.0.1 (use the address the program outputs on
                        start)
  --port PORT, -p PORT  Specify the port to listen at; defaults to 5050
  --load-path LOAD_PATH
                        Specify the path from which the state is loaded on
                        startup
  --dump-path DUMP_PATH
                        Specify the path to dump to
  --dump-on DUMP_ON     Specify when to dump; can dump on: exit, transaction
  --lite-mode           Applies all lite-mode-* optimizations by disabling some features.
  --lite-mode-block-hash
                        Disables block hash calculation
  --lite-mode-deploy-hash
                        Disables deploy tx hash calculation
  --accounts ACCOUNTS   Specify the number of accounts to be predeployed;
                        defaults to 10
  --initial-balance INITIAL_BALANCE, -e INITIAL_BALANCE
                        Specify the initial balance of accounts to be
                        predeployed; defaults to 1e+21 (wei)
  --seed SEED           Specify the seed for randomness of accounts to be
                        predeployed
  --start-time START_TIME
                        Specify the start time of the genesis block in Unix
                        time seconds
  --gas-price GAS_PRICE, -g GAS_PRICE
                        Specify the gas price in wei per gas unit; defaults to
                        1e+11
```

You can run `starknet-devnet` in a separate shell, or you can run it in background with `starknet-devnet &`.
Check that it's alive by running the following (address and port my vary if you specified a different one with `--host` or `--port`):

```
curl http://127.0.0.1:5050/is_alive
```

### Run with Docker

Devnet is available as a Docker image ([shardlabs/starknet-devnet](https://hub.docker.com/repository/docker/shardlabs/starknet-devnet)):

```text
docker pull shardlabs/starknet-devnet:<TAG>
```

#### Versions and Tags

Image tags correspond to Devnet versions as on PyPI and GitHub, with the `latest` tag used for the latest image. These images are built for linux/amd64. To use the arm64 versions, since `0.1.23` you can append `-arm` to the tag. E.g.:

- `shardlabs/starknet-devnet:0.2.4` - image for the amd64 architecture
- `shardlabs/starknet-devnet:0.2.4-arm` - image for the arm64 architecture

The server inside the container listens to the port 5050, which you need to publish to a desired `<PORT>` on your host machine:

```text
docker run -p [HOST:]<PORT>:5050 shardlabs/starknet-devnet
```

E.g. if you want to use your host machine's `127.0.0.1:5050`, you need to run:

```text
docker run -p 127.0.0.1:5050:5050 shardlabs/starknet-devnet
```

You may ignore any address-related output logged on container startup (e.g. `Running on all addresses` or `Running on http://172.17.0.2:5050`). What you will use is what you specified with the `-p` argument.

If you don't specify the `HOST` part, the server will indeed be available on all of your host machine's addresses (localhost, local network IP, etc.), which may present a security issue if you don't want anyone from the local network to access your Devnet instance.

## Interaction

- Interact with Devnet as you would with the official Starknet [Alpha testnet](https://www.cairo-lang.org/docs/hello_starknet/amm.html?highlight=alpha#interaction-examples).
- The exact underlying API is not exposed for the same reason Alpha testnet does not expose it.
- To use Devnet with Starknet CLI, provide Devnet's URL to the `--gateway_url` and `--feeder_gateway_url` options of Starknet CLI commands.
- The following Starknet CLI commands are supported:
  - `call`
  - `declare`
  - `deploy`
  - `estimate_fee`
  - `get_block` (currently pending block is not supported)
  - `get_class_by_hash`
  - `get_class_hash_at`
  - `get_code`
  - `get_full_contract`
  - `get_state_update`
  - `get_storage_at`
  - `get_transaction`
  - `get_transaction_receipt`
  - `get_transaction_trace`
  - `invoke`
  - `tx_status`
- The following Starknet CLI commands are **not** supported:
  - `get_contract_addresses`

## JSON-RPC API

Devnet also partially supports JSON-RPC API (v0.15.0: [specifications](https://github.com/starkware-libs/starknet-specs/blob/606c21e06be92ea1543fd0134b7f98df622c2fbf/api/starknet_api_openrpc.json)). It can be reached under `/rpc`. For an example:

```
POST /rpc
{
  "jsonrpc": "2.0",
  "method": "starknet_protocolVersion",
  "params": [],
  "id": 0
}
```

Response:

```
{
  "id": 0,
  "jsonrpc": "2.0",
  "result": "0x302e382e30"
}
```

## Hardhat integration

If you're using [the Hardhat plugin](https://github.com/Shard-Labs/starknet-hardhat-plugin), see [here](https://github.com/Shard-Labs/starknet-hardhat-plugin#runtime-network) on how to edit its config file to integrate Devnet.

## Postman integration

Postman is a Starknet utility that allows testing L1 <> L2 interaction. To utilize this, you can use [`starknet-hardhat-plugin`](https://github.com/Shard-Labs/starknet-hardhat-plugin), as witnessed in [this example](https://github.com/Shard-Labs/starknet-hardhat-example/blob/master/test/postman.test.ts). Or you can directly interact with the two Postman-specific endpoints:

- Load a `StarknetMockMessaging` contract. The `address` parameter is optional; if provided, the `StarknetMockMessaging` contract will be fetched from that address, otherwise a new one will be deployed:

  - `POST /postman/load_l1_messaging_contract`
  - body: `{ "networkUrl": "http://localhost:8545", "address": "0x83D76591560d9CD02CE16c060c92118d19F996b3" }`
  - `networkUrl` - the URL of the L1 network you've run locally or that already exists; possibilities include, and are not limited to:
    - [Goerli testnet](https://goerli.net/)
    - [Ganache node](https://www.npmjs.com/package/ganache)
    - [Hardhat node](https://hardhat.org/hardhat-network/#running-stand-alone-in-order-to-support-wallets-and-other-software).

- Flush. This will go through the new enqueued messages, sending them from L1 to L2 and from L2 to L1:
  - `POST /postman/flush`
  - body: None

This method of L1 <> L2 communication testing differs from Starknet Alpha networks. Taking the [L1L2Example.sol](https://www.cairo-lang.org/docs/_static/L1L2Example.sol) contract in the [starknet documentation](https://www.cairo-lang.org/docs/hello_starknet/l1l2.html):

```
constructor(IStarknetCore starknetCore_) public {
    starknetCore = starknetCore_;
}
```

The constructor takes an `IStarknetCore` contract as argument, however for Devnet L1 <> L2 communication testing, this will have to be replaced with the [MockStarknetMessaging.sol](https://github.com/starkware-libs/cairo-lang/blob/master/src/starkware/starknet/testing/MockStarknetMessaging.sol) contract:

```
constructor(MockStarknetMessaging mockStarknetMessaging_) public {
    starknetCore = mockStarknetMessaging_;
}
```

## Dumping

To preserve your Devnet instance for future use, there are several options:

- Dumping on exit (handles Ctrl+C, i.e. SIGINT, doesn't handle SIGKILL):

```
starknet-devnet --dump-on exit --dump-path <PATH>
```

- Dumping after each transaction (done in background, doesn't block):

```
starknet-devnet --dump-on transaction --dump-path <PATH>
```

- Dumping on request (replace `<HOST>`, `<PORT>` and `<PATH>` with your own):

```
curl -X POST http://<HOST>:<PORT>/dump -d '{ "path": <PATH> }' -H "Content-Type: application/json"
```

### Loading

To load a preserved Devnet instance, the options are:

- Loading on startup:

```
starknet-devnet --load-path <PATH>
```

- Loading on request:

```
curl -X POST http://<HOST>:<PORT>/load -d '{ "path": <PATH> }' -H "Content-Type: application/json"
```

### Enabling dumping and loading with Docker

To enable dumping and loading if running Devnet in a Docker container, you must bind the container path with the path on your host machine.

This example:

- Relies on [Docker bind mount](https://docs.docker.com/storage/bind-mounts/); try [Docker volume](https://docs.docker.com/storage/volumes/) instead.
- Assumes that `/actual/dumpdir` exists. If unsure, use absolute paths.
- Assumes you are listening on `127.0.0.1:5050`.

If there is `dump.pkl` inside `/actual/dumpdir`, you can load it with:

```
docker run \
  -p 127.0.0.1:5050:5050 \
  --mount type=bind,source=/actual/dumpdir,target=/dumpdir \
  shardlabs/starknet-devnet \
  --load-path /dumpdir/dump.pkl
```

To dump to `/actual/dumpdir/dump.pkl` on Devnet shutdown, run:

```
docker run \
  -p 127.0.0.1:5050:5050 \
  --mount type=bind,source=/actual/dumpdir,target=/dumpdir \
  shardlabs/starknet-devnet \
  --dump-on exit --dump-path /dumpdir/dump.pkl
```

## Block explorer

A local block explorer (Voyager), as noted [here](https://voyager.online/local-version/), apparently cannot be set up to work with Devnet. Read more in [this issue](https://github.com/Shard-Labs/starknet-devnet/issues/60).

## Lite mode

To improve Devnet performance, instead of calculating the actual hash of deployment transactions and blocks, sequential numbering can be used (0x0, 0x1, 0x2, ...).

Consider passing these CLI flags on Devnet startup:

- `--lite-mode` enables all of the optimizations described below (same as using all of the flags below)
- `--lite-mode-deploy-hash`
  - disables the calculation of transaction hash for deploy transactions
- `--lite-mode-block-hash`
  - disables the calculation of block hash
  - disables get_state_update functionality

## Restart

Devnet can be restarted by making a `POST /restart` request. All of the deployed contracts, blocks and storage updates will be restarted to the empty state. If you're using [the Hardhat plugin](https://github.com/Shard-Labs/starknet-hardhat-plugin#restart), run `await starknet.devnet.restart()`.

## Advancing time

Block timestamp can be manipulated by seting the exact time or seting the time offset. Timestamps methods won't generate a new block, but they will modify the time of the following blocks. All values should be set in [Unix time](https://en.wikipedia.org/wiki/Unix_time) and seconds.

### Set time

Sets the exact time of the next generated block. All subsequent blocks will keep the set offset.

```
POST /set_time
{
    "time": TIME_IN_SECONDS
}
```

Warning: block time can be set in the past and lead to unexpected behaviour!

### Increase time

Increases the time offset for each generated block.

```
POST /increase_time
{
    "time": TIME_IN_SECONDS
}
```

### Start time arg

Devnet can be started with the `--start-time` argument.

```
starknet-devnet --start-time START_TIME_IN_SECONDS
```

## Contract debugging

If your contract is using `print` in cairo hints (it was compiled with the `--disable-hint-validation` flag), Devnet will output those lines together with its regular server output. Read more about hints [here](https://www.cairo-lang.org/docs/how_cairo_works/hints.html). To filter out just your debug lines, redirect stderr to /dev/null when starting Devnet:

```
starknet-devnet 2> /dev/null
```

To enable printing with a dockerized version of Devnet set `PYTHONUNBUFFERED=1`:

```
docker run -p 127.0.0.1:5050:5050 -e PYTHONUNBUFFERED=1 shardlabs/starknet-devnet
```

## Predeployed accounts

Devnet predeploys `--accounts` with some `--initial-balance`. The accounts get charged for transactions according to the `--gas-price`. A `--seed` can be used to regenerate the same set of accounts. Read more about it in the [Run section](#run).

To get the code of the account (currently OpenZeppelin v0.1.0), use one of the following:

- `GET /get_code?contractAddress=<ACCOUNT_ADDRESS>`
- [Starknet CLI](https://www.cairo-lang.org/docs/hello_starknet/cli.html#get-code): `starknet get_code --contract_address <ACCOUNT_ADDRESS> --feeder_gateway_url <DEVNET_URL>`
- [OpenZeppelin's cairo-contract repository](https://github.com/OpenZeppelin/cairo-contracts/tree/v0.1.0)

You can use the accounts in e.g. [starknet-hardhat-plugin](https://github.com/Shard-Labs/starknet-hardhat-plugin) via:

```typescript
const account = await starknet.getAccountFromAddress(
  ADDRESS,
  PRIVATE_KEY,
  "OpenZeppelin"
);
```

### Fetch predeployed accounts

```
GET /predeployed_accounts
```

Response:

```
[
  {
    "initial_balance": 1e+21,
    "address": "0x7c3e2...",
    "private_key": "0x6160...",
    "public_key": "0x6a5540..."
  },
  ...
]
```

### Fetch account balance

```
GET /account_balance?address=<HEX_ADDRESS>
```

Response:

```
{
  "amount": 123...456,
  "unit": "wei"
}
```

## Mintable

Used ERC20 Mintable fee Token

### Mint fee token

```
POST /mint
{
    "address": "0x6e3205f...",
    "amount": 500000
}
```

Response:

```
{
    "new_balance": 500000,
    "unit": "wei",
    "tx_hash": 242245223...
}
```

## Devnet speed-up troubleshooting

If you are not satisfied with Devnet's performance, consider the following:

- Make sure you are using the latest version of Devnet because new improvements are added regularly.
- Try using [lite-mode](#lite-mode).
- Using an [installed Devnet](#install) should be faster than [running it with Docker](#run-with-docker).
- If you are [running Devnet with Docker](#run-with-docker) on an ARM machine (e.g. M1), make sure you are using [the appropriate image tag](#versions-and-tags)
- If Devnet has been running for some time, try restarting it (either by killing it or by using the [restart functionality](#restart)).
- Keep in mind that:
  - The first transaction is always a bit slower due to lazy loading.
  - Tools you use for testing (e.g. [the Hardhat plugin](https://github.com/Shard-Labs/starknet-hardhat-plugin)) add their own overhead.
  - Bigger contracts are more time consuming.

## Development

If you're a developer willing to contribute, be sure to have installed [Poetry](https://pypi.org/project/poetry/) and all the dependency packages by running the following script. You are expected to have npm.

```text
./scripts/install_dev_tools.sh
```

### Development - Run

```text
poetry run starknet-devnet
```

### Development - Run in debug mode

```text
./scripts/starknet-devnet-debug.sh
```

### Development - Lint

```text
poetry run pylint starknet_devnet test
```

### Development - Test

When running tests locally, do it from the project root:

```bash
./scripts/compile_contracts.sh # first generate the artifacts

poetry run pytest test/

poetry run pytest -s -v test/ # for more verbose output

poetry run pytest test/<TEST_FILE> # for a single file

poetry run pytest test/<TEST_FILE>::<TEST_CASE> # for a single test case
```

### Development - Check Versioning consistency

```
./scripts/check_versions.sh
```

### Development - Build

You don't need to build anything to be able to run locally, but if you need the `*.whl` or `*.tar.gz` artifacts, run

```text
poetry build
```
