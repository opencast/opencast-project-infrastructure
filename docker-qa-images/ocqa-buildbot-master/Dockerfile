# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v2.3.0
MAINTAINER  Greg Logan

RUN \
    # install cairo for build badges
    apk add --no-cache \
        zlib-dev \
        jpeg-dev \
        build-base \
        python3-dev \
        cairo \
        ttf-dejavu && \
    # install extra pip dependencies not present in upstream image
    pip3 install requests \
                urllib3[secure] \
                txrequests \
                docker \
                buildbot-badges && \
    rm -r /root/.cache

