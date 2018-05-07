#!/bin/bash

#Designed for a directory structure like
#ROOT
# develop
#  build n
#  build m
# X.x
#  build o
#  build p
# Y.x
#  build q
#  build r
#Find all directories under the top level branch dirs, modified outside of the last 30 days
#Then delete them
find "{{ disk_base }}" -mindepth 2 -maxdepth 2 -type d -ctime {{ keep_artifacts }} -exec rm -rf "{}" \;
