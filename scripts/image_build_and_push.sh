#!/bin/bash
set -e

IMAGE=shardlabs/starknet-devnet
VERSION=$(./get-version.sh)

docker build -t $IMAGE:$VERSION -t $IMAGE:latest .
docker login --username $DOCKER_USER --password $DOCKER_PASS
docker push $IMAGE
