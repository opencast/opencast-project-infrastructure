#!/bin/bash

export PGPASSWORD="change_me"

bunzip2 - | psql -h 127.0.0.1 -U buildbot buildbot
