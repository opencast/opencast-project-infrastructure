# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v1.1.0
MAINTAINER  Greg Logan

RUN \
# install extra pip dependencies not present in upstream image
    pip install --upgrade pip setuptools && \
    pip install --upgrade docker==2.6.1 && \ #Required due to https://github.com/docker/docker-py/issues/1916, should be removable soon(tm)
    pip install docker-py && \
    pip install requests && \
    pip install txrequests && \
    pip install docker && \
    rm -r /root/.cache
