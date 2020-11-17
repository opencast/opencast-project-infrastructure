#!/bin/sh

set -u

cd ~

# Download media to ingest
curl -s https://data.lkiesow.io/opencast/test-media/ \
  | sed -n 's/^.*href="\([^"]*\.[^.]..\)".*$/\1/p' \
  | while read -r media
do
  curl -O "https://data.lkiesow.io/opencast/test-media/${media}"
done

# Download additonal open licensed media (Public Domain or Creative Commons)
# PD
curl -o nasa_rocket_test.webm https://upload.wikimedia.org/wikipedia/commons/0/00/NASA%27s_new_High_Dynamic_Range_Camera_Records_Rocket_Test.webm 
curl -O https://tib.flowcenter.de/mfc/medialink/3/de7c76884c990de1084fee40abf6d7fc950610346b64411a76d59f683bd103fc23/22599_C283.mp4
# CC-BY-SA
curl -O https://upload.wikimedia.org/wikipedia/commons/e/e2/1_DOF_Pendulum_with_spring-damper_Adams_simulation.mpg
curl -O https://upload.wikimedia.org/wikipedia/commons/4/43/Espresso_video.ogv
# CC-BY-NC-ND
curl -O https://tib.flowcenter.de/mfc/medialink/3/de2a46cbb86bc3b5933395197e8076295d8fa68480e56f05e3fb081eac51894832/WasistChaos_flash9.mp4


SERVER='http://localhost:8080'
LOGIN='admin:opencast'

# Ensure local Elasticsearch is empty
curl -f -i -u "${LOGIN}" -X POST "${SERVER}/admin-ng/index/clearIndex"
curl -f -i -u "${LOGIN}" -X POST "${SERVER}/api/clearIndex"

# Don't have the user registration pop up every day
# This is allowed to fail
curl -i --request POST -u ${LOGIN} \
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
  -F identifier=ID-about-opencast \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'

# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@ocpr-demo.mp4" \
  -F title="OCPR Demo" \
  -F description="Opencast quick Jira ticket and pull request creator, https://github.com/lkiesow/ocpr" \
  -F creator="Lars Kiesow" \
  -F identifier=ID-ocpr-demo \
  -F license="CC-BY" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'

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

SERIESXML_WIKI='<?xml version="1.0"?>
<dublincore xmlns="http://www.opencastproject.org/xsd/1.0/dublincore/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opencastproject.org http://www.opencastproject.org/schema.xsd" xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/" xmlns:oc="http://www.opencastproject.org/matterhorn/">
  <dcterms:title xml:lang="en">Wiki Commons Content</dcterms:title>
  <dcterms:publisher>Wiki Commons</dcterms:publisher>
  <dcterms:identifier>ID-wiki-commons</dcterms:identifier>
</dublincore>'

SERIESID_WIKI="$(set -ue;
  curl -w "\\n" -s -u "${LOGIN}" \
    -X POST "${SERVER}/series/" \
    --data-urlencode "series=${SERIESXML_WIKI}" \
    --data-urlencode "acl=${SERIESACL}" \
  | sed 's_^.*<dcterms:identifier>\(.*\)</dcterms:identifier>.*$_\1_')"

SERIESXML_TIB='<?xml version="1.0"?>
<dublincore xmlns="http://www.opencastproject.org/xsd/1.0/dublincore/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opencastproject.org http://www.opencastproject.org/schema.xsd" xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/" xmlns:oc="http://www.opencastproject.org/matterhorn/">
  <dcterms:title xml:lang="en">AV-Portal Content</dcterms:title>
  <dcterms:publisher>TIB AV-Portal Hannover</dcterms:publisher>
  <dcterms:identifier>ID-av-portal</dcterms:identifier>
</dublincore>'

SERIESID_TIB="$(set -ue;
  curl -w "\\n" -s -u "${LOGIN}" \
    -X POST "${SERVER}/series/" \
    --data-urlencode "series=${SERIESXML_TIB}" \
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
  -F identifier=ID-tears-of-steel \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'


# Ingest media (Dualstream)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presentation/source" \
  -F "BODY=@dualstream-presentation.mp4" \
  -F flavor="presenter/source" \
  -F "BODY=@dualstream-presenter.mp4" \
  -F title="Dual-Stream Demo" \
  -F creator="Lars Kiesow" \
  -F identifier=ID-dual-stream-demo \
  -F license="CC0" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'


# Ingest media
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@sintel_trailer-1080p.mp4" \
  -F title="Sintel Trailer" \
  -F creator="Durian Open Movie Team" \
  -F description="Trailer for the Sintel open movie project" \
  -F isPartOf="${SERIESID}" \
  -F identifier=ID-sintel-trailer \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'


# Ingest additional open licensed media for testing purposes
# Ingest media (PD)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@nasa_rocket_test.webm" \
  -F title="NASAs new High Dynamic Range Camera Records Rocket Test" \
  -F creator="NASA" \
  -F description="This is footage of Orbital ATK's Space Launch System Qualification Motor 2 (QM-2) solid rocket booster test taken by NASA's High Dynamic Range Stereo X (HiDyRS-X) camera." \
  -F isPartOf="${SERIESID_WIKI}" \
  -F identifier=ID-nasa-rocket-booster \
  -F license="PD" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'

curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@22599_C283.mp4" \
  -F title="Weitsprung" \
  -F creator="Wälken, Paul" \
  -F publisher="Reichsanstalt für Film und Bild in Wissenschaft und Unterricht (RWU)" \
  -F description="Eine Jungenklasse (ca. 16 J.) beim Sportunterricht in straffer Organisation: Lauf im Gelände mit Grabensprüngen. Beispiele von Sprüngen in Schrittfolgetechnik. Schrittsprünge mit kurzem Anlauf unter Betonung der Streckung im Absprung und des Steigenlassens im Fluge. Ermitteln der Anlauflänge und Festlegen der Ablaufmarke. Weitsprünge in guter und fehlerhafter Ausführung. Mit Zeitdehnung. Aufgenommen mit 20 B/s; Vorführgeschw. 18 B/s." \
  -F isPartOf="${SERIESID_TIB}" \
  -F identifier=ID-weitsprung \
  -F license="PD" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'

# Ingest media (CC-BY-SA)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@1_DOF_Pendulum_with_spring-damper_Adams_simulation.mpg" \
  -F title="DOF Pendulum with spring-damper Adams simulation" \
  -F creator="I. Elgamal" \
  -F description="1 DOF Pendulum with spring-damper Adams simulation with input vibration" \
  -F isPartOf="${SERIESID_WIKI}" \
  -F identifier=ID-pendulum-with-spring-damper \
  -F license="CC-BY-SA" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'

# Ingest media (CC-BY-SA)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@Espresso_video.ogv" \
  -F title="Espresso_video" \
  -F creator="Rosatrieu" \
  -F description="The video shows how espresso is typically made." \
  -F isPartOf="${SERIESID_WIKI}" \
  -F identifier=ID-espresso-video \
  -F license="CC-BY-SA" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'

# Ingest media (CC-BY-NC-ND)
curl -f -i -s -D - -o /dev/null -u ${LOGIN} \
  "${SERVER}/ingest/addMediaPackage/fast" \
  -F flavor="presenter/source" \
  -F "BODY=@WasistChaos_flash9.mp4" \
  -F title="Was ist Chaos?, Folge 16, Experiment der Woche." \
  -F creator="Skorupka, Sascha" \
  -F publisher="Leibniz Universität Hannover (LUH)" \
  -F isPartOf="${SERIESID_TIB}" \
  -F identifier=ID-was-ist-chaos \
  -F license="CC-BY-NC-ND" \
  -F acl='{"acl": {"ace": [{"allow": true,"role": "ROLE_ANONYMOUS","action": "read"}]}}'
