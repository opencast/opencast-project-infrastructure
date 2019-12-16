#!/bin/sh

REMOTE=opencast

#set -o xtrace
set -o nounset
set -o errexit

# create bucket
minio-mc mb "${REMOTE}/public"
minio-mc mb "${REMOTE}/private"
minio-mc mb "${REMOTE}/internal"

# get policy
# minio-mc admin policy info local readonly | jq > readonly-test.json
# possibly add s3:ListBucket
TMPDIR=$(mktemp -d)
# internal
minio-mc admin policy info "${REMOTE}" readonly \
  | jq ".Statement[].Resource[] = \"arn:aws:s3:::private/*\"
        | .Statement[0].Action += [\"s3:ListBucket\"]" \
          > "${TMPDIR}/private-readonly.json"
minio-mc admin policy info "${REMOTE}" writeonly \
  | jq ".Statement[].Resource[] = \"arn:aws:s3:::private/*\"" \
          > "${TMPDIR}/private-writeonly.json"
minio-mc admin policy info "${REMOTE}" readwrite \
  | jq ".Statement[].Resource[] = \"arn:aws:s3:::private/*\"" \
          > "${TMPDIR}/private-readwrite.json"
# public
minio-mc admin policy info "${REMOTE}" readwrite \
  | jq ".Statement[].Resource[] = \"arn:aws:s3:::public/*\"" \
          > "${TMPDIR}/public-readwrite.json"

cd "${TMPDIR}"
for policy in *json; do

  # add new policies
  minio-mc admin policy add "${REMOTE}" "${policy%.json}" "${policy}"

  # add new users
  key="${policy%.json}-$(pwgen -n1 16)"
  secret="$(pwgen -n1 64)"
  echo "${key}  ${secret}"
  minio-mc admin user add "${REMOTE}" "${key}" "${secret}"

  # apply policy to user
  minio-mc admin policy set "${REMOTE}" "${policy%.json}" "user=${key}"

done

# make public bucket public (read access only)
minio-mc policy set download "${REMOTE}/public"

rm -irf "${TMPDIR}"
