#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan

doBuild() {
  cd ocqa-$1-$2
  docker build -t $DOCKER_OWNER/$(basename `pwd`) .
  cd ..
}

doBuildWorker() {
  doBuild $1 build
  doBuild $1 doc
  doBuild $1 package
  doBuild $1 worker
}

doBuildWorker deb9


