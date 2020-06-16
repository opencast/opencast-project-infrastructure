#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan
TAG=latest

doBuild() {
  bash build-container.sh $DOCKER_OWNER $1 $2 $TAG
}

doBuild buildbot master
doBuild ubu16 worker-base
doBuild ubu18 worker-base
doBuild ubu20 worker-base
doBuild deb9 worker-base
doBuild deb10 worker-base
doBuild cent7 worker-base
doBuild cent8 worker-base
