#!/bin/bash

DOCKER_OWNER=greglogan
TAG=latest
if [ $# -gt 2 -o $# -lt 1 ]; then
  echo "Usage: $0 TAG [upstream]"
  exit 1
elif [ $# -eq 1 ]; then
  TAG=$1
elif [ $# -eq 2 ]; then
  TAG=$1
  DOCKER_OWNER=$2
fi

doPush() {
  bash push-container.sh $DOCKER_OWNER $1 $2 $TAG
}

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  doPush $image worker-base
done
doPush buildbot master
