#!/bin/sh
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

# Ensure access to log files
mkdir -p /srv/opencast/opencast-dist-allinone/data/log
restorecon -r /srv/opencast/ || :
chcon -Rt httpd_sys_content_t /srv/opencast/opencast-dist-allinone/data/log || :
chcon -R system_u:object_r:bin_t:s0 /srv/opencast/opencast-dist-allinone/bin/ || :

# Clear Elasticsearch
sudo systemctl stop elasticsearch.service
sudo rm -rf /var/lib/elasticsearch/nodes
sudo systemctl restart elasticsearch.service

sleep 10

if [ ! -d /usr/share/elasticsearch/plugins/analysis-icu ]; then
  #If the analysis-icu directory does not exist, install the thing
  /usr/share/elasticsearch/bin/elasticsearch-plugin install -b analysis-icu
fi

# Start Opencast
sudo systemctl start opencast.service

# Wait until Opencast is up before ingesting media
sleep 120
./ingest.py

# Avoid registration form
curl -i -s -u admin:opencast \
	'http://127.0.0.1:8080/admin-ng/adopter/registration' \
	--data-raw 'contactMe=false&allowsStatistics=false&allowsErrorReports=false&agreedToPolicy=false&organisationName=&departmentName=&country=&postalCode=&city=&firstName=&lastName=&street=&streetNo=&email=&registered='
