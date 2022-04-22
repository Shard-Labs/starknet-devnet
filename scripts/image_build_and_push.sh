#!/bin/bash
set -e

[ -f .env ] && source .env

IMAGE=shardlabs/starknet-devnet
LOCAL_VERSION=$(./scripts/get_version.sh version)
echo "Local version: $LOCAL_VERSION"

LOCAL_VERSION_TAG="${LOCAL_VERSION}${TAG_SUFFIX}"
LATEST_VERSION_TAG="latest$TAG_SUFFIX"

echo "Build image regardless of versioning"
docker build -t "$IMAGE:$LOCAL_VERSION_TAG" -t "$IMAGE:$LATEST_VERSION_TAG" .

echo "Run a devnet instance in background; sleep to allow it to start"
# can't use "localhost" because docker doesn't allow such mapping
docker run -d -p 127.0.0.1:5000:5000 --name devnet "$IMAGE:$LATEST_VERSION_TAG"
sleep 10
docker logs devnet

echo "Checking if devnet instance is alive"
if [ ! -z $REMOTE ]; then
    ssh remote-docker curl localhost:5000/is_alive
else
    curl localhost:5000/is_alive
fi

# curling the url fails with 404
function docker_image_exists() {
    curl --silent -f -lSL "$1" > /dev/null 2>&1
}

function log_already_pushed() {
    echo "Latest Docker Hub version is already equal to the local version."
    echo "Pushing skipped"
}

function push() {
    docker login --username "$DOCKER_USER" --password "$DOCKER_PASS"
    docker push "$IMAGE:$LOCAL_VERSION_TAG"
    docker push "$IMAGE:$LATEST_VERSION_TAG"
}

dockerhub_url="https://hub.docker.com/v2/repositories/$IMAGE/tags/$LOCAL_VERSION_TAG"
docker_image_exists "$dockerhub_url" && log_already_pushed || push
