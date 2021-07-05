#!/bin/bash

if [ $# -ne 5 ]; then
  echo "Usage: $0 IMAGE_OWNER IMAGE_SOURCE BASE_OS IMAGE_TYPE TAG"
  echo " eg: $0 greglogan greglogan deb9 worker v1.4.0 -> tags greglogan/ocqa-deb9-worker:latest as greglogan/ocqa-deb9-worker:v1.4.0"
  exit 1
fi

set -uxe

IMAGE_TARGET=$1
IMAGE_SRC=$2
IMAGE_OS=$3
IMAGE_TYPE=$4
IMAGE_TAG=$5

LATEST_TAG="$IMAGE_SRC/ocqa-$IMAGE_OS-$IMAGE_TYPE:latest"
IMAGE_TAG="$IMAGE_TARGET/ocqa-$IMAGE_OS-$IMAGE_TYPE:$IMAGE_TAG"

if [ $# -eq 5 -a "latest" != $IMAGE_TAG ]; then
  docker tag $LATEST_TAG $IMAGE_TAG
fi

