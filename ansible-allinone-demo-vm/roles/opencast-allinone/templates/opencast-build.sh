#!/bin/sh
set -uex

{% if 'legacy' in inventory_hostname %}
branch="{{opencast_legacy_branch}}"
version="{{opencast_legacy_version}}"

{% elif 'stable' in inventory_hostname %}
branch="{{opencast_stable_branch}}"
version="{{opencast_stable_version}}"

{% else %}
branch="{{opencast_develop_branch}}"
version="{{opencast_develop_version}}"

{% endif %}

cd ~

# Get latest opencast
curl -s -O "http://build.opencast.org/builds/${branch}/opencast-dist-allinone-${version}.tar.gz"
tar xf opencast-dist-allinone-*.tar.gz
rm opencast-dist-allinone-*.tar.gz

# Stop and remove old Opencast
sudo systemctl stop opencast.service || :
rm -rf /srv/opencast/opencast-dist-allinone

# Set-up new Opencast
mv opencast-dist-allinone /srv/opencast/
sed -i 's#^org.opencastproject.server.url=.*$#org.opencastproject.server.url=https://{{inventory_hostname}}#' /srv/opencast/opencast-dist-allinone/etc/custom.properties

# Ensure access to log files
mkdir -p /srv/opencast/opencast-dist-allinone/data/log
chcon -Rt httpd_sys_content_t /srv/opencast/opencast-dist-allinone/data/log || :

# Update ActiveMQ cofniguration
sudo install -m 644 /srv/opencast/opencast-dist-allinone/docs/scripts/activemq/activemq.xml /etc/activemq/activemq.xml
sudo systemctl restart activemq.service || :

# Start Opencast
sudo systemctl start opencast.service

# Wait until Opencast is up before ingesting media
sleep 180
cd /home/opencast
./opencast-ingest.sh
