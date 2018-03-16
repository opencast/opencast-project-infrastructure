#!/bin/bash

set -uxe

apt-get update
apt-get install -y wget ca-certificates apt-transport-https
wget -qO - {{ oc_deb_repo_key }} | apt-key add -
echo "{{ oc_deb_repo_url }}" | tee /etc/apt/sources.list.d/opencast.list
