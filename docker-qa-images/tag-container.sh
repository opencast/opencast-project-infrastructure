#!/bin/bash

if [ $# -ne 4 ]; then
  echo "Usage: $0 IMAGE_OWNER BASE_OS IMAGE_TYPE TAG"
  echo " eg: $0 greglogan deb9 worker v1.4.0 -> builds v1.4.0"
  exit 1
fi

set -uxe

LATEST_TAG="$1/ocqa-$2-$3:latest"
IMAGE_TAG="$1/ocqa-$2-$3:$4"

cd ocqa-$2-$3
if [ $# -eq 4 -a "latest" != $4 ]; then
  docker tag $LATEST_TAG $IMAGE_TAG
fi
cd ..

