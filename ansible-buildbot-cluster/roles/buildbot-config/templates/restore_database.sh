#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 backup.bz2"
  exit 1
fi

if [ $(curl -s 'https://{{ inventory_hostname }}/api/v2/builds?limit=10' | jq -r '.meta.total') -lt 1 ]; then
  echo "Restoring"
  docker compose down
  rm -rf postgres-data
  docker compose up -d db
  sleep 30
  cat $1 | bunzip2 - | docker compose -f /opt/buildbot/docker-compose.yml exec -T db bash -c 'PGPASSWORD=change_me psql -h db -U buildbot buildbot'
  docker compose up -d
else
  echo "Refusing to restore to an already active buildbot system"
fi
