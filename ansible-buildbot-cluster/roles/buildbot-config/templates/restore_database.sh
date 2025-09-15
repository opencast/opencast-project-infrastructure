#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 backup.bz2"
  exit 1
fi

cat $1 | bunzip2 - | docker compose -f /opt/buildbot/docker-compose.yml exec -T db bash -c 'PGPASSWORD=change_me psql -h db -U buildbot buildbot'
