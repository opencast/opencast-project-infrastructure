#!/bin/sh

set -ue

cd ~

# Download media to ingest
curl -s https://data.lkiesow.io/opencast/test-media/ \
  | sed -n 's/^.*href="\([^"]*\.[^.]..\)".*$/\1/p' \
  | while read -r media
do
  curl -O "https://data.lkiesow.io/opencast/test-media/${media}"
done

SERVER='http://localhost:8080'
LOGIN='admin:opencast'

curl -f -i -u "${LOGIN}" -X POST "${SERVER}/admin-ng/index/clearIndex"
curl -f -i -u "${LOGIN}" -X POST "${SERVER}/api/clearIndex"

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presentation/source" \
  -F "BODY=@olaf-schulte-opencast.mp4" \
  -F title="About Opencast" \
  -F creator="Olaf Schulte"

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presentation/source" \
  -F "BODY=@ocpr-demo.mp4" \
  -F title="OCPR Demo" \
  -F description="Opencast quick Jira ticket and pull request creator, https://github.com/lkiesow/ocpr" \
  -F creator="Lars Kiesow"

# opencast series ACL to be used for new series
SERIESACL='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<acl xmlns="http://org.opencastproject.security"></acl>'

# opencast series dublincore catalog template
SERIESXML='<?xml version="1.0"?>
<dublincore xmlns="http://www.opencastproject.org/xsd/1.0/dublincore/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opencastproject.org http://www.opencastproject.org/schema.xsd" xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/" xmlns:oc="http://www.opencastproject.org/matterhorn/">
  <dcterms:title xml:lang="en">Blender Foundation Productions</dcterms:title>
  <dcterms:publisher>Blender Foundation</dcterms:publisher>
</dublincore>'

SERIESID="$(set -ue;
  curl -w "\\n" -s -u "${LOGIN}" \
    -X POST "${SERVER}/series/" \
    --data-urlencode "series=${SERIESXML}" \
    --data-urlencode "acl=${SERIESACL}" \
  | sed 's_^.*<dcterms:identifier>\(.*\)</dcterms:identifier>.*$_\1_')"

VIDEO_FILE_PRESENTATION=ToS-slides-4k-1920.mp4
VIDEO_FILE_PRESENTER=ToS-4k-1920.mov

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@${VIDEO_FILE_PRESENTER}" \
  -F title="Tears of Steel" \
  -F creator="Blender Foundation" \
  -F isPartOf="${SERIESID}"

# Ingest media (Dualstream)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presentation/source" \
  -F "BODY=@${VIDEO_FILE_PRESENTATION}" \
  -F flavor="presenter/source" \
  -F "BODY=@${VIDEO_FILE_PRESENTER}" \
  -F title="Tears of Steel (Dualstream)" \
  -F creator="Blender Foundation" \
  -F isPartOf="${SERIESID}"

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@sintel_trailer-1080p.mp4" \
  -F title="Sintel Trailer" \
  -F creator="Durian Open Movie Team" \
  -F description="Trailer for the Sintel open movie project" \
  -F isPartOf="${SERIESID}"
