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

doBuild() {
  bash build-container.sh $DOCKER_OWNER $1 $2 $TAG
  docker image prune -f
}

for i in 18.04 20.04
do
  docker pull ubuntu:$i
done
for i in 9 10 11
do
  docker pull debian:$i
done
docker pull centos:7
docker pull rockylinux/rockylinux:8

doBuild buildbot master
doBuild ubu18 worker-base
doBuild ubu20 worker-base
doBuild deb9 worker-base
doBuild deb10 worker-base
doBuild deb11 worker-base
doBuild cent7 worker-base
doBuild rocky8 worker-base
