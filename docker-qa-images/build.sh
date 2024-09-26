#!/bin/bash

DOCKER_OWNER=greglogan
DOCKER_TAG=latest
BUILDBOT_VERSION="v3.9.2"
BUILD_DATE="`date --iso-8601`"

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
  docker build . --pull --build-arg VERSION="$BUILDBOT_VERSION" --build-arg BUILD_DATE="$BUILD_DATE" --target base -t $DOCKER_OWNER/ocqa-$image-worker-base:$DOCKER_TAG
  grep "AS jdk" Dockerfile | cut -f 4 -d " " | while read jdk
  do
    docker build . --build-arg VERSION="$BUILDBOT_VERSION" --build-arg BUILD_DATE="$BUILD_DATE" --target $jdk -t $DOCKER_OWNER/ocqa-$image-worker-base-$jdk:$DOCKER_TAG
  done
  popd  2>&1 > /dev/null
done
cd ocqa-buildbot-master
docker build .  --build-arg BUILD_DATE="$BUILD_DATE" -t $DOCKER_OWNER/ocqa-buildbot-master:$DOCKER_TAG
cd ..

docker image prune -f

