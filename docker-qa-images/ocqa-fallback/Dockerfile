FROM debian:13

#Needed to work around pip bug: https://githubmemory.com/repo/pypa/pip/issues/10219
ARG LANG=C.UTF-8
ARG LC_ALL=C.UTF-8
ARG VERSION=unknown
ARG BUILD_DATE=unknown

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.title="Opencast QA Debian 13 Fallback Image" \
      org.opencontainers.image.description="Opencast QA fallback image based on a Debian 13 environment" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="Opencast" \
      org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.url="https://github.com/opencast/opencast-project-infrastructure/docker-qa-images" \
      org.opencontainers.image.source="https://github.com/opencast/opencast-project-infrastructure" \
      org.opencontainers.image.created="${BUILD_DATE}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo \
        apt-transport-https \
        gnupg \
        curl \
        ca-certificates \
        git \
        bash \
        openssh-client && \
    apt-get clean

RUN mkdir -p /etc/apt/keyrings/
COPY keys/* /etc/apt/keyrings/
COPY repos/* /etc/apt/sources.list.d/

#Install bits only needed for docker and buildbot
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        docker-ce-cli && \
    apt-get clean

    # Test runs produce a great quantity of dead grandchild processes.  In a
    # non-docker environment, these are automatically reaped by init (process 1),
    # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

#Allow buildbot to install packages (ffmpeg) later
RUN echo "buildbot ALL = (root) NOPASSWD : /usr/bin/apt-get, /usr/bin/yum, /usr/local/bin/dumb-init, /bin/sed" > /etc/sudoers.d/buildbot

COPY buildbot.tac /builder/buildbot.tac
    # Install required python packages, and twisted
RUN python3 -m pip --no-cache-dir install future buildbot-worker==${VERSION} --break-system-packages
