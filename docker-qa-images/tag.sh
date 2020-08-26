#!/bin/bash

set -uxe

if [ $# -ne 1 ]; then
    echo "Usage: $0 TAG"
    exit 1
fi

DOCKER_OWNER=greglogan
TAG=$1

doTag() {
  bash tag-container.sh $DOCKER_OWNER $1 $2 $TAG
}

doTag buildbot master
doTag ubu16 worker-base
doTag ubu18 worker-base
doTag ubu20 worker-base
doTag deb9 worker-base
doTag deb10 worker-base
doTag cent7 worker-base
doTag cent8 worker-base
