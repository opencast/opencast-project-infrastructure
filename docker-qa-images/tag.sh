#!/bin/bash

set -uxe

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

doTag() {
  bash tag-container.sh $DOCKER_OWNER $1 $2 $TAG
}

doTag buildbot master
doTag ubu18 worker-base
doTag ubu20 worker-base
doTag deb9 worker-base
doTag deb10 worker-base
doTag cent7 worker-base
doTag cent8 worker-base
