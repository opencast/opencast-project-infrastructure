FROM buildbot/buildbot-master:v4.1.0
# This overlay adds a few missing bits required for Opencast's use of BuildBot, notably requests (to power Github)

ARG BUILD_DATE

LABEL org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.title="Opencast Buildbot Master Image" \
      org.opencontainers.image.description="Opencast QA image based on the upstream image" \
      org.opencontainers.image.version="v3.9.2" \
      org.opencontainers.image.vendor="Opencast" \
      org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.url="https://github.com/opencast/opencast-project-infrastructure/docker-qa-images" \
      org.opencontainers.image.source="https://github.com/opencast/opencast-project-infrastructure" \
      org.opencontainers.image.created="${BUILD_DATE}"

RUN /buildbot_venv/bin/pip3 --no-cache-dir install docker
RUN /buildbot_venv/bin/pip3 --no-cache-dir install PyGitHub
RUN /buildbot_venv/bin/pip3 --no-cache-dir install boto3

