#!/bin/bash

DOCKER_OWNER=greglogan
DOCKER_TAG=latest
BUILDBOT_VERSION="v4.3.0"
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
  grep 'FROM .* AS' Dockerfile | sed 's/.* AS \(.*\)/\1/g' | while read subimage
  do
    docker build . --pull --build-arg VERSION="$BUILDBOT_VERSION" --build-arg BUILD_DATE="$BUILD_DATE" --target $subimage -t $DOCKER_OWNER/ocqa-$image-worker-base-$subimage:$DOCKER_TAG
  done
  #Special handling, retag the -base-base image as -base
  docker tag $DOCKER_OWNER/ocqa-$image-worker-base-base:$DOCKER_TAG $DOCKER_OWNER/ocqa-$image-worker-base:$DOCKER_TAG
  popd  2>&1 > /dev/null
done
cd ocqa-buildbot-master
docker build .  --build-arg BUILD_DATE="$BUILD_DATE" -t $DOCKER_OWNER/ocqa-buildbot-master:$DOCKER_TAG
cd ..

docker image prune -f

