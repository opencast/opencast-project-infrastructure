#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan

doPush() {
  bash push-container.sh $DOCKER_OWNER $1 $2
}

doPushWorker() {
  doPush $1 worker
  doPush $1 package
  doPush $1 doc
  doPush $1 build
  doPush $1 run
}

doPushWorker deb9


