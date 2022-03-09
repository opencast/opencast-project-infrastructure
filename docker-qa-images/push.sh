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

doPush buildbot master
doPush deb9 worker-base
doPush deb10 worker-base
doPush deb11 worker-base
doPush ubu18 worker-base
doPush ubu20 worker-base
doPush cent7 worker-base
doPush rocky8 worker-base
