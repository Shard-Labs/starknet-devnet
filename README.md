## Introduction
A Flask wrapper of Starknet state. Similar in purpose to Ganache.

Aims to mimic Starknet's Alpha testnet, but with simplified functionality.

## Install
```text
pip install starknet-devnet
```

## Requirements
Works with Python versions <=3.9.7.

On Ubuntu/Debian, first run:
```text
sudo apt install -y libgmp3-dev
```

On Mac, you can use `brew`:
```text
brew install gmp
```

## Disclaimer
- This devnet should not be used as a replacement for Alpha testnet. After testing on devnet, be sure to test on testnet!
- Hash calculation of transactions and blocks differs from the one used in Alpha testnet.
- Specifying a block by its hash/number is not supported. All interaction is done with the latest block.
- Read more in [interaction](#interaction-api).

## Run
Installing the package adds the `starknet-devnet` command.
```text
usage: starknet-devnet [-h] [-v] [--host HOST] [--port PORT]

Run a local instance of Starknet devnet

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Print the version
  --host HOST           Specify the address to listen at; defaults to localhost (use the address the program outputs on start)
  --port PORT, -p PORT  Specify the port to listen at; defaults to 5000
```

## Run - Docker
This devnet is available as a Docker container ([shardlabs/starknet-devnet](https://hub.docker.com/repository/docker/shardlabs/starknet-devnet)):
```text
docker pull shardlabs/starknet-devnet
```

The server inside the container listens to the port 5000, which you need to publish to a desired `<PORT>` on your host machine:
```text
docker run -it -p [HOST:]<PORT>:5000 shardlabs/starknet-devnet
```
E.g. if you want to use your host machine's `127.0.0.1:5000`, you need to run:
```text
docker run -it -p 127.0.0.1:5000:5000 shardlabs/starknet-devnet
```
You may ignore any address-related output logged on container startup (e.g. `Running on all addresses` or `Running on http://172.17.0.2:5000`). What you will use is what you specified with the `-p` argument.

If you don't specify the `HOST` part, the server will indeed be available on all of your host machine's addresses (localhost, local network IP, etc.), which may present a security issue if you don't want anyone from the local network to access your devnet.

## Interaction
- Interact with this devnet as you would with the official Starknet [Alpha testnet](https://www.cairo-lang.org/docs/hello_starknet/amm.html?highlight=alpha#interaction-examples).
- The exact underlying API is not exposed for the same reason Alpha testnet does not expose it.
- The following Starknet CLI commands are supported:
  - `call`
  - `deploy`
  - `get_block`
  - `get_code`
  - `get_storage_at`
  - `get_transaction`
  - `invoke`
  - `tx_status`
  - `get_transaction_receipt`:
    - returns complete data for invoke transactions
    - returns partial data for deploy transactions
- The following Starknet CLI commands are **not** supported:
  - `get_contract_addresses` - L1-L2 interaction is currently not supported

## Hardhat integration
- If you're using [the Hardhat plugin](https://github.com/Shard-Labs/starknet-hardhat-plugin), see [here](https://github.com/Shard-Labs/starknet-hardhat-plugin#testing-network) on how to edit its config file to integrate this devnet.

## Development - Prerequisite
If you're a developer willing to contribute, be sure to have installed [Poetry](https://pypi.org/project/poetry/).

## Development - Run
```text
poetry run starknet-devnet
```

## Development - Test
When running tests locally, do it from the project root.

Setup an example project by running:
```text
./scripts/setup_example.sh
```

To see if the devnet can interact with starknet CLI commands, run:
```text
./scripts/test_cli.sh
```

To see if the devnet can interact with the plugin, run:
```text
./scripts/test_plugin.sh
```

## Development - Build
```text
poetry build
```
