#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan
TAG=v2.3.1

doPush() {
  bash push-container.sh $DOCKER_OWNER $1 $2 $TAG
}

doPushWorker() {
  doPush $1 worker-base
  doPush $1 package
  doPush $1 doc
  doPush $1 build
  doPush $1 run
  doPush $1 package-stripped
}

doPushWorker deb9
doPushWorker cent7


