#!/bin/bash

gpg --batch --yes --output Release.gpg --local-user {{ signing_key_id }} --detach-sign "$1"
