# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v2.7.0
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
RUN pip3 install requests \
                urllib3[secure] \
                txrequests \
                docker \
                buildbot-badges \
                cryptography pyasn1 bcrypt && \
    rm -r /root/.cache

