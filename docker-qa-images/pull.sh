#!/bin/bash

DOCKER_OWNER=greglogan
DOCKER_TAG=latest
BUILDBOT_VERSION="v4.3.0"

if [ $# -gt 1 ]; then
  echo "Usage: $0 [TAG]"
  exit 1
elif [ $# -eq 1 ]; then
  DOCKER_TAG=$1
fi

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  pushd . 2>&1 > /dev/null
  cd ocqa-$image-worker-base
  docker pull $DOCKER_OWNER/ocqa-$image-worker-base:$DOCKER_TAG
  grep "AS jdk" Dockerfile | cut -f 4 -d " " | while read jdk
  do
    docker pull $DOCKER_OWNER/ocqa-$image-worker-base-$jdk:$DOCKER_TAG
  done
  popd 2>&1 > /dev/null
done
docker pull $DOCKER_OWNER/ocqa-buildbot-master:$DOCKER_TAG

docker image prune -f
