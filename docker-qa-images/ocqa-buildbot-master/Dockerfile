# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v2.8.3
MAINTAINER  Greg Logan

# install cairo for build badges
RUN apk add --no-cache \
        zlib-dev \
        jpeg-dev \
        build-base \
        python3-dev \
        cairo \
        ttf-dejavu \
        # required for manhole debug
        libffi-dev
    # install extra pip dependencies not present in upstream image
RUN python3 -m pip --no-cache-dir install \
                requests \
                urllib3[secure] \
                txrequests \
                docker \
                buildbot-badges \
                cryptography pyasn1 bcrypt

