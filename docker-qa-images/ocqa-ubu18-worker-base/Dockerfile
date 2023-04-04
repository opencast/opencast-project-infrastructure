FROM ubuntu:18.04
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#Needed to work around pip bug: https://githubmemory.com/repo/pypa/pip/issues/10219
ARG LANG=C.UTF-8
ARG LC_ALL=C.UTF-8
ARG VERSION=unknown
ARG BUILD_DATE=unknown

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.title="Opencast QA Ubuntu 18.04 Image" \
      org.opencontainers.image.description="Opencast QA image based on an Ubuntu 18.04 environment" \
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
        ca-certificates && \
    apt-get clean

RUN mkdir -p /etc/apt/keyrings/
COPY keys/* /etc/apt/keyrings/
COPY repos/* /etc/apt/sources.list.d/

COPY aws-config /builder/.aws/config
COPY install-ffmpeg.sh /builder/install-ffmpeg.sh

RUN chmod 755 /builder/install-ffmpeg.sh

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        locales \
     # Run deps
        tesseract-ocr \
        netcat \
        sox \
        hunspell \
	openjdk-11-jre \
	openjdk-17-jre \
     # Build deps
        openssh-client \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        openjdk-11-jdk \
        openjdk-17-jdk \
        firefox && \
    apt-get clean

#Requires appimage, which doesn't work in Docker.
#and appimagetool's extraction is not yet implemented, despite being documented as the 'solution' here
#RUN curl --silent "https://api.github.com/repos/synfig/synfig/releases/latest" | \
#    grep "browser_download_url.*linux64*" | \
#    cut -d : -f 2,3 | tr -d \" | wget -qi - -O /usr/bin/synfig && \
#    chmod 755 /usr/bin/synfig

RUN apt-get install -y --no-install-recommends \
     # Doc deps
     ## Python deps
        python3-dev \
        python3-pip \
     ## Packages for building docs
        libyaml-dev \
        nodejs && \
    apt-get clean

RUN apt-get install -y --no-install-recommends \
     # Package building deps
     # Note: build-essential is required for dpkg, gcc is required for python
        build-essential \
        dpkg-dev \
        debhelper \
        devscripts \
        dh-exec \
        libdistro-info-perl \
        fakeroot \
     # s3fs since aptly needs it
        s3fs \
     # Crowdin
        crowdin && \
    apt-get install -y -t squeeze aptly && \
    apt-get clean

RUN update-java-alternatives -s java-1.11.0-openjdk-amd64

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# de_DE.UTF-8 UTF-8/de_DE.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

RUN python3 -m pip --no-cache-dir install --upgrade pip
RUN python3 -m pip --no-cache-dir install --upgrade setuptools
    # Ansible deploy bits
RUN python3 -m pip --no-cache-dir install ansible paramiko
    # Buildbot s3 deploy bits
RUN python3 -m pip --no-cache-dir install awscli
    # Vosk, notably without any language models
RUN python3 -m pip --no-cache-dir install vosk webvtt-py

#Install bits only needed for docker setup
RUN apt-get install -y docker-ce-cli && \
    apt-get clean

    # Test runs produce a great quantity of dead grandchild processes.  In a
    # non-docker environment, these are automatically reaped by init (process 1),
    # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

COPY opencast.list /etc/apt/sources.list.d
RUN echo "buildbot ALL = (root) NOPASSWD : /usr/bin/apt-get, /usr/bin/yum, /usr/local/bin/dumb-init, /bin/sed" > /etc/sudoers.d/buildbot

COPY buildbot.tac /builder/buildbot.tac
    # Install required python packages, and twisted
RUN python3 -m pip --no-cache-dir install future buildbot-worker==${VERSION}
