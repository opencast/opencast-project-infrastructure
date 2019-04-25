#!/bin/bash

gpg --batch --yes --output Release.gpg --local-user {{ oc_deb_repo_key_id }} --detach-sign "$1"
