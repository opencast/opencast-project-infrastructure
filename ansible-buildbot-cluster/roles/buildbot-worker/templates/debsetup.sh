#!/bin/bash

set -uxe

wget -qO - {{ oc_deb_repo_key }} | apt-key add -
echo "{{ oc_deb_repo_url }}" | tee /etc/apt/sources.list.d/opencast.list
echo "{{ oc_deb_repo_url_testing }}" | tee /etc/apt/sources.list.d/opencast-testing.list
apt-get update
apt-get install -y ffmpeg
