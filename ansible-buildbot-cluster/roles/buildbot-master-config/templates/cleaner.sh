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
# builds
#  X.x
#  Y.x
# reports
#  X.x
#  Y.x
#Find all directories under the top level branch dirs, modified outside of the last 30 days
#Then delete them
find "{{ disk_base }}" -mindepth 2 -maxdepth 2 -xtype d -mtime +{{ keep_artifacts }} -exec rm -rf "{}" \;
#Clean up any dangling symlinks
find "{{ disk_base }}" -mindepth 2 -maxdepth 2 -xtype l -exec rm -rf "{}" \;
