#!/bin/bash

if [ $# -ne 3 ]; then
  echo "Usage: $0 IMAGE_OWNER BASE_OS IMAGE_TYPE"
  echo " eg: $0 greglogan deb9 worker"
  exit 1
fi

set -uxe

IMAGE_TAG="$1/ocqa-$2-$3"
cd ocqa-$2-$3
docker push $IMAGE_TAG
cd ..

