FROM ubuntu:20.04
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#Needed to work around pip bug: https://githubmemory.com/repo/pypa/pip/issues/10219
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https gnupg curl ca-certificates && \
    apt-get clean

RUN mkdir /root/apt-keys
COPY keys/* /root/apt-keys/
RUN apt-key add /root/apt-keys/*

COPY opencast.list /etc/apt/sources.list.d
COPY opencast-test.list /etc/apt/sources.list.d
COPY nodesource.list /etc/apt/sources.list.d
COPY aptly.list /etc/apt/sources.list.d
COPY crowdin.list /etc/apt/sources.list.d

COPY aws-config /builder/.aws/config

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2022-03-07

RUN apt-get update

RUN apt-get install -y --no-install-recommends \
        bash \
        locales \
     # Run deps
        tesseract-ocr \
        netcat \
        synfig \
        sox \
        hunspell \
        ffmpeg-dist \
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

RUN apt-get install -y --no-install-recommends \
     # Doc deps
     ## Python deps
        python3-dev \
        python3-pip \
     ## Packages for building docs
        libyaml-dev \
        nodejs && \
     ## For SQL script testing
     #  mysql-client && \
    apt-get clean

RUN apt-get install -y --no-install-recommends \
     # Package building deps
     # Note: build-essential is required for dpkg, gcc is required for python
        build-essential \
        dpkg-dev \
        debhelper \
        devscripts \
        dh-exec \
        aptly=1.4.0 \
        libdistro-info-perl \
        fakeroot \
     # s3fs since aptly needs it
        s3fs \
     # Crowdin
        crowdin && \
    apt-get clean

RUN update-java-alternatives -s java-1.11.0-openjdk-amd64

RUN python3 -m pip --no-cache-dir install --upgrade pip
RUN python3 -m pip --no-cache-dir install --upgrade setuptools
    # Ansible deploy bits
RUN python3 -m pip --no-cache-dir install ansible paramiko
    # Buildbot s3 deploy bits
RUN python3 -m pip --no-cache-dir install awscli
    # Release deploy bits

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# de_DE.UTF-8 UTF-8/de_DE.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

    # Test runs produce a great quantity of dead grandchild processes.  In a
    # non-docker environment, these are automatically reaped by init (process 1),
    # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

COPY buildbot.tac /builder/buildbot.tac
     # Install required python packages, and twisted
RUN python3 -m pip --no-cache-dir install future buildbot-worker==3.5.0

