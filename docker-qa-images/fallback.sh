#!/bin/bash

DOCKER_OWNER=s3.loganite.ca
DOCKER_TAG=latest
BUILDBOT_VERSION="v4.3.0"

cd ocqa-fallback
docker build . --build-arg VERSION="$BUILDBOT_VERSION" -t $DOCKER_OWNER/ocqa-fallback:$DOCKER_TAG
cd ..

ls | grep worker-base | grep -v fallback | while read name
do
  docker tag $DOCKER_OWNER/ocqa-fallback:$DOCKER_TAG $DOCKER_OWNER/$name:$DOCKER_TAG
done
docker rmi $DOCKER_OWNER/ocqa-fallback:$DOCKER_TAG
