#!/bin/bash

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
