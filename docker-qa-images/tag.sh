#!/bin/bash

DOCKER_OWNER=greglogan
TAG=latest
if [ $# -gt 3 -o $# -lt 1 ]; then
  echo "Usage: $0 TAG [upstream] [source_upstream]"
  echo " eg: $0 v3.1.1 $DOCKER_OWNER -> Tag all $DOCKER_OWNER/ocqa-*:latest as $DOCKER_OWNER/ocqa-*:v3.1.1"
  echo " eg: $0 v3.1.1 $DOCKER_OWNER internal_registry -> Tag all internal_registry/ocqa-*:latest as $DOCKER_OWNER/ocqa-*:v3.1.1"
  exit 1
elif [ $# -eq 1 ]; then
  TAG=$1
elif [ $# -eq 2 ]; then
  TAG=$1
  DOCKER_OWNER=$2
elif [ $# -eq 3 ]; then
  TAG=$1
  DOCKER_OWNER=$2
  DOCKER_SOURCE=$3
fi

doTag() {
  bash tag-container.sh $DOCKER_OWNER $DOCKER_SOURCE $1 $2 $TAG
}

ls | grep worker-base | cut -f 2 -d "-" | while read image
do
  doTag $image worker-base
done
doTag buildbot master

