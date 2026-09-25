#!/bin/bash

DOCKER_OWNER=greglogan
DOCKER_TAG=latest

if [ $# -gt 1 ]; then
  echo "Usage: $0 [TAG]"
  exit 1
elif [ $# -eq 1 ]; then
  DOCKER_TAG=$1
fi

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  pushd . > /dev/null 2>&1
  cd "ocqa-$image-worker-base" || exit
  docker pull "$DOCKER_OWNER/ocqa-$image-worker-base-core:$DOCKER_TAG"
  docker pull "$DOCKER_OWNER/ocqa-$image-worker-base:$DOCKER_TAG"
  grep "FROM .* AS .*" Dockerfile | cut -f 4 -d " " | grep jdk | while read -r subimage
  do
    docker pull "$DOCKER_OWNER/ocqa-$image-worker-base-$subimage:$DOCKER_TAG"
  done
  popd > /dev/null 2>&1 || exit
done
docker pull "$DOCKER_OWNER/ocqa-buildbot-master:$DOCKER_TAG"

docker image prune -f
