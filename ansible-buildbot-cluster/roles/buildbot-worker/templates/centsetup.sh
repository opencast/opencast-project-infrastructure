#!/bin/bash

set -uxe

echo "[opencast]
name = Opencast el 7 Repository
baseurl  = {{ oc_rpm_repo_url }}
username = {{ repo_username }}
password = {{ repo_password }}
enabled  = 1
gpgcheck = 1
gpgkey = {{ oc_rpm_repo_key }}

[opencast-noarch]
name = Opencast el 7 Repository - noarch
baseurl  = {{ oc_rpm_repo_url_noarch }}
username = {{ repo_username }}
password = {{ repo_password }}
enabled  = 1
gpgcheck = 1
gpgkey = {{ oc_rpm_repo_key }}
" | tee /etc/yum.repos.d/opencast.repo

echo "[opencast-testing]
name = Opencast el 7 Testing Repository
baseurl  = {{ oc_rpm_repo_url_testing }}
username = {{ repo_username }}
password = {{ repo_password }}
enabled  = 1
gpgcheck = 1
gpgkey = {{ oc_rpm_repo_key }}

[opencast-testing-noarch]
name = Opencast el 7 Testing Repository - noarch
baseurl  = {{ oc_rpm_repo_url_noarch_testing }}
username = {{ repo_username }}
password = {{ repo_password }}
enabled  = 1
gpgcheck = 1
gpgkey = {{ oc_rpm_repo_key }}
" | tee /etc/yum.repos.d/opencast-testing.repo
yum update
yum install -y ffmpeg
