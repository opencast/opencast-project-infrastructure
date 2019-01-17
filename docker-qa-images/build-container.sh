#!/bin/bash

if [ $# -ne 4 ]; then
  echo "Usage: $0 IMAGE_OWNER BASE_OS IMAGE_TYPE TAG"
  echo " eg: $0 greglogan deb9 worker v1.4.0"
  exit 1
fi

set -uxe

IMAGE_TAG="$1/ocqa-$2-$3:$4"
cd ocqa-$2-$3
docker build -t $IMAGE_TAG .
cd ..

