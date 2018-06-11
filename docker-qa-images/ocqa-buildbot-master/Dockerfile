# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v1.2.0
MAINTAINER  Greg Logan

RUN \
# install extra pip dependencies not present in upstream image
    pip install --upgrade pip setuptools && \
    pip install requests \
                urllib3[secure] \
                txrequests \
                docker && \
    rm -r /root/.cache
