#!/bin/bash

docker compose -f /opt/buildbot/docker-compose.yml exec -t db bash -c 'PGPASSWORD=change_me pg_dump -h db -d buildbot -U buildbot' \
| bzip2 -9 -
