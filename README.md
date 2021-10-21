## Introduction
A Flask wrapper of Starknet dummy network. Similar in purpose to Ganache.

## Install
```text
pip install starknet-devnet
```

On Ubuntu/Debian, first run:
```text
sudo apt install -y libgmp3-dev
```

On Mac, you can use `brew`:
```text
brew install gmp
```

## Run
```text
usage: starknet-devnet [-h] [--host HOST] [--port PORT]

Run a local instance of Starknet devnet

optional arguments:
  -h, --help   show this help message and exit
  --host HOST  the address to listen at; defaults to localhost (use the address the program outputs on start)
  --port PORT  the port to listen at; defaults to 5000
```

## Run - Docker
This devnet is available as a Docker container ([shardlabs/starknet-devnet](https://hub.docker.com/repository/docker/shardlabs/starknet-devnet)):
```text
docker pull shardlabs/starknet-devnet
```

The server inside the container listens to the port 5000, which you need to publish to a desired `<PORT>`:
```text
docker run -it -p [HOST:]<PORT>:5000 shardlabs/starknet-devnet
```
E.g. if you want to use your host machine's `127.0.0.1:5000`, you need to run:
```text
docker run -it -p 127.0.0.1:5000:5000 shardlabs/starknet-devnet
```
If you don't specify `HOST:`, the server will be available on all of your host machine's addresses (localhost, local network IP, etc.).

## Important notes
- Types in call/invoke:
  - You will NOT be able to pass or receive values of type other than `felt` and `felt*`.

## Interaction
Interact with this devnet as you would with the official Starknet [alpha network](https://www.cairo-lang.org/docs/hello_starknet/amm.html?highlight=alpha#interaction-examples).

## Hardhat integration
- Be sure to read [Important notes](#important-notes).
- If you're using [the Hardhat plugin](https://github.com/Shard-Labs/starknet-hardhat-plugin), see [here](https://github.com/Shard-Labs/starknet-hardhat-plugin#testing-network) on how to edit its config file to integrate this devnet.

## Development - Prerequisite
If you're a developer willing to contribute, be sure to have installed [Poetry](https://pypi.org/project/poetry/).

## Development - Run
```text
poetry run starknet-devnet
```

## Development - Build
```text
poetry build
```
