#!/bin/bash
set -uex

cd /opt/opencast-build/

# Clean up first of we are out of space (<300MB free)
free_space="$(df --output=avail . | tail -n1)"
if [ "${free_space}" -lt 300000 ]; then
  rm -rf /srv/opencast/opencast-dist-allinone/data/opencast/
fi

# Get latest opencast
curl -s -O https://radosgw.public.os.wwu.de/opencast-daily/opencast-dist-allinone-{{ version }}.tar.gz
tar xf opencast-dist-allinone-*.tar.gz
rm opencast-dist-allinone-*.tar.gz

# Stop and remove old Opencast
sudo systemctl stop opencast.service || :
rm -rf /srv/opencast/opencast-dist-allinone

# Set-up new Opencast
mv opencast-dist-allinone /srv/opencast/
sed -i 's#^org.opencastproject.server.url=.*$#org.opencastproject.server.url=https://{{ inventory_hostname }}#' /srv/opencast/opencast-dist-allinone/etc/custom.properties

# Enable capture agent user
sed -i 's/^#capture_agent.user.mh_default_org.opencast_capture_agent/capture_agent.user.mh_default_org.opencast_capture_agent/' \
	/srv/opencast/opencast-dist-allinone/etc/org.opencastproject.userdirectory.InMemoryUserAndRoleProvider.cfg

# Configure LTI
sed -i 's_<!-- \(<ref.*oauthProtectedResourceFilter.*/>\) -->_\1_' /srv/opencast/opencast-dist-allinone/etc/security/mh_default_org.xml
sed -i 's_#oauth_oauth_' /srv/opencast/opencast-dist-allinone/etc/org.opencastproject.kernel.security.OAuthConsumerDetailsService.cfg

echo "# The catalog type, either 'events' or 'series'
type=series

# The tenants organization
organization=mh_default_org

# The mediapackage element flavor type and subtype
# Anything can be used instead of "mycompany", for example "metadata", "client", etc.
# Note: The flavor should not contain any special character!
flavor=ethterms/series

# The title of the catalog
# This will show in the header of the section where the metadata are displayed
title=ETH Extended Metadata


# Name of the XML root element of the serialized catalog
xml.rootElement.name=ethterms
# Namespace binding for the XML root element
xml.rootElement.namespace.URI=http://ethz.ch/video/opencast

# XML namespace bindings
xml.namespaceBinding.root.URI=http://ethz.ch/video/opencast
xml.namespaceBinding.root.prefix=
xml.namespaceBinding.terms.URI=http://ethz.ch/video/metadata
xml.namespaceBinding.terms.prefix=ethterms


##### Field Definitions #####

# Advertised
property.advertised.inputID=advertised
property.advertised.label=Advertised
property.advertised.type=boolean
property.advertised.readOnly=false
property.advertised.required=false
property.advertised.namespace=http://ethz.ch/video/metadata
property.advertised.order=1

# Subtype
property.subtype.inputID=subtype
property.subtype.label=Subtype
property.subtype.type=text
property.subtype.readOnly=false
property.subtype.required=false
property.subtype.namespace=http://ethz.ch/video/metadata
property.subtype.order=2

# Episodes
property.episodes.inputID=episodes
property.episodes.label=Episodes
property.episodes.type=text
property.episodes.readOnly=false
property.episodes.required=false
property.episodes.namespace=http://ethz.ch/video/metadata
property.episodes.order=3

# VP URL 1
property.vpUrl1.inputID=vpUrl1
property.vpUrl1.label=VP URL 1
property.vpUrl1.type=text
property.vpUrl1.readOnly=false
property.vpUrl1.required=false
property.vpUrl1.namespace=http://ethz.ch/video/metadata
property.vpUrl1.order=4

# VP URL 2
property.vpUrl2.inputID=vpUrl2
property.vpUrl2.label=VP URL 2
property.vpUrl2.type=text
property.vpUrl2.readOnly=false
property.vpUrl2.required=false
property.vpUrl2.namespace=http://ethz.ch/video/metadata
property.vpUrl2.order=5

# MMP URL Old 1
property.mmpUrlOld1.inputID=mmpUrlOld1
property.mmpUrlOld1.label=MMP URL Old 1
property.mmpUrlOld1.type=text
property.mmpUrlOld1.readOnly=false
property.mmpUrlOld1.required=false
property.mmpUrlOld1.namespace=http://ethz.ch/video/metadata
property.mmpUrlOld1.order=6

# MMP URL Old 2
property.mmpUrlOld2.inputID=mmpUrlOld2
property.mmpUrlOld2.label=MMP URL Old 2
property.mmpUrlOld2.type=text
property.mmpUrlOld2.readOnly=false
property.mmpUrlOld2.required=false
property.mmpUrlOld2.namespace=http://ethz.ch/video/metadata
property.mmpUrlOld2.order=7

# DOI Prefix
property.doiPrefix.inputID=doiPrefix
property.doiPrefix.label=DOI Prefix
property.doiPrefix.type=text
property.doiPrefix.readOnly=false
property.doiPrefix.required=false
property.doiPrefix.namespace=http://ethz.ch/video/metadata
property.doiPrefix.order=8

# DOI ID
property.doiId.inputID=doiId
property.doiId.label=DOI ID
property.doiId.type=text
property.doiId.readOnly=false
property.doiId.required=false
property.doiId.namespace=http://ethz.ch/video/metadata
property.doiId.order=9

# Department
property.department.inputID=department
property.department.label=Department
property.department.type=text
property.department.readOnly=false
property.department.required=false
property.department.namespace=http://ethz.ch/video/metadata
property.department.order=10

# SHIS
property.shis.inputID=shis
property.shis.label=SHIS
property.shis.type=text
property.shis.readOnly=false
property.shis.required=false
property.shis.namespace=http://ethz.ch/video/metadata
property.shis.order=11

# Reverse Order
property.reverseOrder.inputID=reverseOrder
property.reverseOrder.label=Reverse Order
property.reverseOrder.type=text
property.reverseOrder.readOnly=false
property.reverseOrder.required=false
property.reverseOrder.namespace=http://ethz.ch/video/metadata
property.reverseOrder.order=12

# VVZ
property.vvz.inputID=vvz
property.vvz.label=VVZ
property.vvz.type=text
property.vvz.readOnly=false
property.vvz.required=false
property.vvz.namespace=http://ethz.ch/video/metadata
property.vvz.order=13

# Semester
property.semester.inputID=semester
property.semester.label=Semester
property.semester.type=text
property.semester.readOnly=false
property.semester.required=false
property.semester.namespace=http://ethz.ch/video/metadata
property.semester.order=14

# Notes
property.notesSeries.inputID=notesSeries
property.notesSeries.label=Notes
property.notesSeries.type=text
property.notesSeries.readOnly=false
property.notesSeries.required=false
property.notesSeries.namespace=http://ethz.ch/video/metadata
property.notesSeries.order=15

# URL
property.urlSeries.inputID=urlSeries
property.urlSeries.label=URL
property.urlSeries.type=text
property.urlSeries.readOnly=false
property.urlSeries.required=false
property.urlSeries.namespace=http://ethz.ch/video/metadata
property.urlSeries.order=16

# Legacy Series ID
property.legacySeriesId.inputID=legacySeriesId
property.legacySeriesId.label=Legacy Series ID
property.legacySeriesId.type=text
property.legacySeriesId.readOnly=false
property.legacySeriesId.required=false
property.legacySeriesId.namespace=http://ethz.ch/video/metadata
property.legacySeriesId.order=17" > /srv/opencast/opencast-dist-allinone/etc/org.opencastproject.ui.metadata.CatalogUIAdapterFactory-series-ethterms.cfg

echo "type=series
organization=*
title=Series Metadata
flavor=dublincore/series
common-metadata=true

# Name of the XML root element of the serialized catalog
xml.rootElement.name=dublincore
# Namespace binding for the XML root element
xml.rootElement.namespace.URI=http://www.opencastproject.org/xsd/1.0/dublincore/

# XML namespace bindings
xml.namespaceBinding.root.URI=http://www.opencastproject.org/xsd/1.0/dublincore/
xml.namespaceBinding.root.prefix=
xml.namespaceBinding.dc.URI=http://purl.org/dc/elements/1.1/
xml.namespaceBinding.dc.prefix=dc
xml.namespaceBinding.dcterms.URI=http://purl.org/dc/terms/
xml.namespaceBinding.dcterms.prefix=dcterms

# Title
property.title.inputID=title
property.title.label=EVENTS.SERIES.DETAILS.METADATA.TITLE
property.title.type=text
property.title.readOnly=false
property.title.required=true
property.title.order=0

# Unique ID for Series
property.uid.inputID=identifier
property.uid.label=EVENTS.SERIES.DETAILS.METADATA.ID
property.uid.type=text
property.uid.readOnly=true
property.uid.required=false
property.uid.order=10

# Publishers
property.publisher.inputID=publisher
property.publisher.label=EVENTS.SERIES.DETAILS.METADATA.PUBLISHERS
property.publisher.type=mixed_text
property.publisher.readOnly=false
property.publisher.required=true
property.publisher.listprovider=PUBLISHERS
property.publisher.order=8

# Contributors
property.contributor.inputID=contributor
property.contributor.label=EVENTS.SERIES.DETAILS.METADATA.CONTRIBUTORS
property.contributor.type=mixed_text
property.contributor.delimiter=;
property.contributor.readOnly=false
property.contributor.required=false
# property.contributor.listprovider=CONTRIBUTORS
property.contributor.order=7

# Organizers
property.organizer.inputID=creator
property.organizer.label=EVENTS.SERIES.DETAILS.METADATA.ORGANIZERS
property.organizer.type=mixed_text
property.organizer.delimiter=;
property.organizer.readOnly=false
property.organizer.required=false
# property.organizer.listprovider=CONTRIBUTORS
property.organizer.order=6

# Subject
property.subject.inputID=subject
property.subject.label=EVENTS.SERIES.DETAILS.METADATA.SUBJECT
property.subject.type=text
property.subject.readOnly=false
property.subject.required=false
property.subject.order=1

# Language
property.language.inputID=language
property.language.label=EVENTS.SERIES.DETAILS.METADATA.LANGUAGE
property.language.type=text
property.language.readOnly=false
property.language.required=true
property.language.listprovider=LANGUAGES
property.language.order=3

# Description
property.description.inputID=description
property.description.label=EVENTS.SERIES.DETAILS.METADATA.DESCRIPTION
property.description.type=text_long
property.description.readOnly=false
property.description.required=false
property.description.order=2

# Rights
property.rightsHolder.inputID=rightsHolder
property.rightsHolder.label=EVENTS.SERIES.DETAILS.METADATA.RIGHTS
property.rightsHolder.type=ordered_text
property.rightsHolder.readOnly=false
property.rightsHolder.required=true
property.rightsHolder.listprovider=RIGHTS
property.rightsHolder.order=4

# License
property.license.inputID=license
property.license.label=EVENTS.SERIES.DETAILS.METADATA.LICENSE
property.license.type=ordered_text
property.license.readOnly=false
property.license.required=true
property.license.listprovider=LICENSES
property.license.order=5" > /srv/opencast/opencast-dist-allinone/etc/org.opencastproject.ui.metadata.CatalogUIAdapterFactory-series-common.cfg


# Ensure access to log files
mkdir -p /srv/opencast/opencast-dist-allinone/data/log
restorecon -r /srv/opencast/ || :
chcon -Rt httpd_sys_content_t /srv/opencast/opencast-dist-allinone/data/log || :
chcon -R system_u:object_r:bin_t:s0 /srv/opencast/opencast-dist-allinone/bin/ || :

# Clear OpenSearch
sudo systemctl stop opensearch.service
sudo rm -rf /var/lib/opensearch/nodes
sudo systemctl restart opensearch.service

# Wait for OpenSearch to be available
curl -fisS --retry 60 --retry-delay 1 --retry-all-errors \
  http://localhost:9200/

# Start Opencast
sudo systemctl start opencast.service

# Wait until Opencast is up before ingesting media
# Initialize the counter
counter=1
# This takes a while right now beacuse of https://github.com/opencast/opencast/issues/7755
# Loop while the counter is less than or equal to 5
while (( counter <= 10 )); do
  if [ $(curl -s -o /dev/null -w '%{http_code}' -f --digest -u 'opencast_system_account:CHANGE_ME' -H 'X-Requested-Auth: Digest'  http://localhost/info/me.json) -eq 200 ]; then
    echo "Opencast ready"
    break
  fi
  echo "Opencast not ready"
  ((counter++))
  sleep 60
done

./ingest.py

# Avoid registration form
curl -i -s -u admin:opencast \
	'http://127.0.0.1:8080/admin-ng/adopter/registration' \
	--data-raw 'contactMe=false&allowsStatistics=false&allowsErrorReports=false&agreedToPolicy=false&organisationName=&departmentName=&country=&postalCode=&city=&firstName=&lastName=&street=&streetNo=&email=&registered='

# Add test users
echo "Start adding users: $(date +%s)"
for i in {00000..25000}
do
  curl -s -u admin:opencast 'http://127.0.0.1:8080/user-utils/' \
    -F username="u${i}" \
    -F password="p${i}" \
    -F 'roles=["ROLE_TEST"]' \
    -F name="$(shuf -n 1 /usr/share/dict/words || echo user) $(shuf -n 1 /usr/share/dict/words || echo "${i}")"
done
echo "Finished adding users: $(date +%s)"

# Add test series
echo "Start adding series: $(date +%s)"
for i in {00000..15000}
do
  curl -s -u admin:opencast 'http://127.0.0.1:8080/series/' \
    -F title="$(shuf -n 1 /usr/share/dict/words || echo "s${i}")" \
    -F identifier="s${i}"
done
echo "Finished adding series: $(date +%s)"

# add creators and series to metadata selector
curl -u admin:opencast http://127.0.0.1:8080/ingest/addMediaPackage/fast \
	-F 'flavor=presenter/source' \
	-F mediaUri=https://data.lkiesow.io/opencast/test-media/goat.mp4 \
	-F creator='Lars Kiesow' \
	$(for i in {00000..25000}; do echo "-F contributor=u${i}"; done) \
	$(for i in {00000..15000}; do echo "-F isPartOf=s${i}"; done) \
	-F title=test
