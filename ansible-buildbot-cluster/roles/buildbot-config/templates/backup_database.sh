#!/bin/bash

export PGPASSWORD="change_me"

pg_dump -h 127.0.0.1 -U buildbot buildbot | bzip2 -9 - > `date -u +'%FT%H%M%S'`.pgsql.bz2
