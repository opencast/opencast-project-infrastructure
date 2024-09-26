#!/bin/bash

DOCKER_OWNER=greglogan
DOCKER_SOURCE=greglogan
DOCKER_TAG=latest
if [ $# -gt 3 -o $# -lt 1 ]; then
  echo "Usage: $0 TAG [upstream] [source_upstream]"
  echo " eg: $0 v3.1.1 $DOCKER_OWNER -> Tag all $DOCKER_OWNER/ocqa-*:latest as $DOCKER_OWNER/ocqa-*:v3.1.1"
  echo " eg: $0 v3.1.1 $DOCKER_OWNER internal_registry -> Tag all internal_registry/ocqa-*:latest as $DOCKER_OWNER/ocqa-*:v3.1.1"
  exit 1
elif [ $# -eq 1 ]; then
  DOCKER_TAG=$1
elif [ $# -eq 2 ]; then
  DOCKER_TAG=$1
  DOCKER_OWNER=$2
elif [ $# -eq 3 ]; then
  DOCKER_TAG=$1
  DOCKER_OWNER=$2
  DOCKER_SOURCE=$3
fi

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  pushd . 2>&1 > /dev/null
  docker tag $DOCKER_SOURCE/ocqa-$image-worker-base:latest $DOCKER_OWNER/ocqa-$image-worker-base:$DOCKER_TAG
  grep "AS jdk" ocqa-$image-worker-base/Dockerfile | cut -f 4 -d " " | while read jdk
  do
  docker tag $DOCKER_SOURCE/ocqa-$image-worker-base-$jdk:latest $DOCKER_OWNER/ocqa-$image-worker-base-$jdk:$DOCKER_TAG
  done
  popd  2>&1 > /dev/null
done
docker tag $DOCKER_SOURCE/ocqa-buildbot-master:latest $DOCKER_OWNER/ocqa-buildbot-master:$DOCKER_TAG

