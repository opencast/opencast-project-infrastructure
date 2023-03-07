#!/bin/bash

DOCKER_OWNER=greglogan
TAG=latest
if [ $# -gt 1 ]; then
  echo "Usage: $0 [TAG]"
  exit 1
elif [ $# -eq 1 ]; then
  TAG=$1
fi

doBuild() {
  bash build-container.sh $DOCKER_OWNER $1 $2 $TAG
  docker image prune -f
}

ls | grep ubu | cut -f 2 -d "-" | cut -c 4- | while read major
do
  docker pull ubuntu:$major.04
done

ls | grep deb | cut -f 2 -d "-" | cut -c 4- | while read major
do
  docker pull debian:$major
done

docker pull centos:7
docker pull quay.io/centos/centos:stream8
docker image prune -f

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  doBuild $image worker-base
done
doBuild buildbot master
