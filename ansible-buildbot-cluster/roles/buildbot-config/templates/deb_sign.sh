#!/bin/bash

gpg --batch --yes --output Release.gpg --local-user {{ hostvars[groups['master'][0]]['signing_key_id'] | default(signing_key_id) }} --detach-sign "$1"
