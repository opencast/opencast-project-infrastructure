#!/bin/bash

if [ $# -ne 3 ]; then
  echo "Usage: $0 uid gid oc_version"
  exit 1
fi

groupadd -g $2 builder && \
useradd -m -u $1 -g $2 -s /bin/bash -d /builder builder && \
mkdir -p /builder/.ssh /builds && \
chown -R builder:builder /builder /builds && \
sed -i "s/FIXME/$3/g" /etc/yum.repos.d/opencast.repo && \
sudo yum install -y ffmpeg && \

sudo /usr/local/bin/dumb-init twisted --pidfile= -ny buildbot.tac
