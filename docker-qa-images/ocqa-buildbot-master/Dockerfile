# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v1.2.0
MAINTAINER  Greg Logan

RUN \
    # install cairo for build badges
    apk add --no-cache cairo && \
    # install extra pip dependencies not present in upstream image
    pip install --upgrade pip setuptools && \
    pip install requests \
                urllib3[secure] \
                txrequests \
                docker \
                buildbot-badges && \
    rm -r /root/.cache

COPY *.py /usr/lib/python2.7/site-packages/buildbot_badges/
COPY *.svg.j2 /usr/lib/python2.7/site-packages/buildbot_badges/templates/
