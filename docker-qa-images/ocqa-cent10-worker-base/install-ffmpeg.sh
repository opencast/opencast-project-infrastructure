#!/bin/bash

export branch=`echo $1 | cut -c -2`
if command -v apt-get > /dev/null; then 
  sudo -n sed -i "s/FIXME/$branch.x/g" /etc/apt/sources.list.d/opencast.list && \
  sudo -n apt-get update && \
  sudo -n apt-get install -y ffmpeg-dist
elif command -v yum > /dev/null; then 
  sudo -n sed -i "s/FIXME/$branch/g" /etc/yum.repos.d/opencast.repo && \
  #NB two spaces to keep things aligned, do not change unless repo file changes!
  sudo -n sed -i 's/enabled  = 0/enabled  = 1/g' /etc/yum.repos.d/opencast.repo && \
  sudo -n yum install -y ffmpeg
fi
