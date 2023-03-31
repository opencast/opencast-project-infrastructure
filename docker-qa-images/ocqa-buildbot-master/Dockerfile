# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v3.7.0
MAINTAINER  Greg Logan

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2022-03-07

# install cairo for build badges
RUN apt-get update && \
    apt-get dist-upgrade -y

RUN /buildbot_venv/bin/pip3 --no-cache-dir install docker
RUN /buildbot_venv/bin/pip3 --no-cache-dir install PyGitHub
RUN /buildbot_venv/bin/pip3 --no-cache-dir install boto3

#RUN apk add --no-cache \
#        zlib-dev \
#        jpeg-dev \
#        build-base \
#        python3-dev \
#        cairo \
#        ttf-dejavu \
#        # required for manhole debug
#        libffi-dev
#    # install extra pip dependencies not present in upstream image
#RUN python3 -m pip --no-cache-dir install \
#                requests \
#                urllib3[secure] \
#                txrequests \
#                docker \
#                buildbot-badges \
#                cryptography pyasn1 bcrypt

