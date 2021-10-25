#!/bin/bash
set -e

[ -f .env ] && source .env

# idea from: https://stackoverflow.com/a/50945459
# returns "yes" or "no" instead of exit code so as to be able to use the benefits of `set -e`
function docker_tag_exists() {
    curl --silent -f -lSL https://hub.docker.com/v2/repositories/$1/tags/$2 > /dev/null 2>&1 && echo "yes" || echo "no"
}

IMAGE=shardlabs/starknet-devnet
LOCAL_VERSION=$(./scripts/get-version.sh)
echo "Local version: $LOCAL_VERSION"

# Building is executed regardless of versions
docker build -t $IMAGE:$LOCAL_VERSION -t $IMAGE:latest .

if [ $(docker_tag_exists $IMAGE $LOCAL_VERSION) = "yes" ]; then
    echo "Latest Docker Hub version is already equal to the local version."
    echo "Pushing skipped"
else
    docker login --username "$DOCKER_USER" --password "$DOCKER_PASS"
    docker push $IMAGE:$LOCAL_VERSION
    docker push $IMAGE:latest
fi
