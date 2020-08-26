#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan
TAG=latest
if [ $# -gt 1 ]; then
  echo "Usage: $0 [TAG]"
  exit 1
elif [ $# -eq 1 ]; then
  TAG=$1
fi

doPush() {
  bash push-container.sh $DOCKER_OWNER $1 $2 $TAG
}

doPush buildbot master
doPush deb9 worker-base
doPush deb10 worker-base
doPush ubu16 worker-base
doPush ubu18 worker-base
doPush ubu20 worker-base
doPush cent7 worker-base
doPush cent8 worker-base
