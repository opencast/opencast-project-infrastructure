#!/bin/bash

HOME=/mnt/aptly GNUPGHOME=/mnt/aptly/.gnupg gpg --import /mnt/aptly/signing.key

HOME=/mnt/aptly GNUPGHOME=/mnt/aptly/.gnupg aptly -config=/mnt/aptly/aptly.conf api serve
