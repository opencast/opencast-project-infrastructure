#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan
TAG=latest

doPush() {
  bash push-container.sh $DOCKER_OWNER $1 $2 $TAG
}

doPush buildbot master
doPush deb9 worker-base
doPush deb10 worker-base
doPush cent7 worker-base
doPush cent8 worker-base
