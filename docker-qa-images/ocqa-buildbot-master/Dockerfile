# opencast/buildbot-master

# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

FROM        buildbot/buildbot-master:v3.7.0
MAINTAINER  Greg Logan

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ARG BUILD_DATE=unknown

# install cairo for build badges
RUN apt-get update && \
    apt-get dist-upgrade -y

RUN /buildbot_venv/bin/pip3 --no-cache-dir install docker
RUN /buildbot_venv/bin/pip3 --no-cache-dir install PyGitHub
RUN /buildbot_venv/bin/pip3 --no-cache-dir install boto3

