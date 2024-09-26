#!/bin/bash

DOCKER_OWNER=greglogan
DOCKER_TAG=latest

if [ $# -gt 2 -o $# -lt 1 ]; then
  echo "Usage: $0 TAG [upstream]"
  exit 1
elif [ $# -eq 1 ]; then
  DOCKER_TAG=$1
elif [ $# -eq 2 ]; then
  DOCKER_TAG=$1
  DOCKER_OWNER=$2
fi

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  pushd . 2>&1 > /dev/null
  cd ocqa-$image-worker-base
  docker push $DOCKER_OWNER/ocqa-$image-worker-base:$DOCKER_TAG
  grep "AS jdk" Dockerfile | cut -f 4 -d " " | while read jdk
  do
    docker push $DOCKER_OWNER/ocqa-$image-worker-base-$jdk:$DOCKER_TAG
  done
  popd 2>&1 > /dev/null
done
cd ocqa-buildbot-master
docker push $DOCKER_OWNER/ocqa-buildbot-master:$DOCKER_TAG
cd ..
