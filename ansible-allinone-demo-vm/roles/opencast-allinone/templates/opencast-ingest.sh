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

# Ensure local Elasticsearch is empty
curl -f -i -u "${LOGIN}" -X POST "${SERVER}/admin-ng/index/clearIndex"
curl -f -i -u "${LOGIN}" -X POST "${SERVER}/api/clearIndex"

# Don't have the user registration pop up every day
# This is allowed to fail
curl -i --request POST -u admin:opencast \
  --header "Content-Type: application/json" \
  --data '{"contactMe":false,"allowsStatistics":false,"allowsErrorReports":false,"agreedToPolicy":false}' \
  "${SERVER}/admin-ng/adopter/registration"

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@olaf-schulte-opencast.mp4" \
  -F title="About Opencast" \
  -F creator="Olaf Schulte" \
  -F identifier=ID-about-opencast

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@ocpr-demo.mp4" \
  -F title="OCPR Demo" \
  -F description="Opencast quick Jira ticket and pull request creator, https://github.com/lkiesow/ocpr" \
  -F creator="Lars Kiesow" \
  -F identifier=ID-ocpr-demo

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
  <dcterms:identifier>ID-blender-foundation</dcterms:identifier>
</dublincore>'

SERIESID="$(set -ue;
  curl -w "\\n" -s -u "${LOGIN}" \
    -X POST "${SERVER}/series/" \
    --data-urlencode "series=${SERIESXML}" \
    --data-urlencode "acl=${SERIESACL}" \
  | sed 's_^.*<dcterms:identifier>\(.*\)</dcterms:identifier>.*$_\1_')"

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@ToS-4k-1920.mov" \
  -F title="Tears of Steel" \
  -F creator="Blender Foundation" \
  -F isPartOf="${SERIESID}" \
  -F identifier=ID-tears-of-steel


# Ingest media (Dualstream)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presentation/source" \
  -F "BODY=@dualstream-presentation.mp4" \
  -F flavor="presenter/source" \
  -F "BODY=@dualstream-presenter.mp4" \
  -F title="Dual-Stream Demo" \
  -F creator="Lars Kiesow" \
  -F identifier=ID-dual-stream-demo


# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@sintel_trailer-1080p.mp4" \
  -F title="Sintel Trailer" \
  -F creator="Durian Open Movie Team" \
  -F description="Trailer for the Sintel open movie project" \
  -F isPartOf="${SERIESID}" \
  -F identifier=ID-sintel-trailer
