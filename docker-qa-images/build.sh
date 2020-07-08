#!/bin/bash

set -uxe

DOCKER_OWNER=greglogan
TAG=latest

doBuild() {
  bash build-container.sh $DOCKER_OWNER $1 $2 $TAG
  docker image prune -f
}

for i in 16.04 18.04 20.04
do
  docker pull ubuntu:$i
done
for i in 9 10
do
  docker pull debian:$i
done
for i in 7 8
do
  docker pull centos:$i
done

doBuild buildbot master
doBuild ubu16 worker-base
doBuild ubu18 worker-base
doBuild ubu20 worker-base
doBuild deb9 worker-base
doBuild deb10 worker-base
doBuild cent7 worker-base
doBuild cent8 worker-base
