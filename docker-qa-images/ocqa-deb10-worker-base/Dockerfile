FROM debian:10
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https gnupg curl ca-certificates && \
    apt-get clean

RUN curl -fsSL https://pkg.opencast.org/gpgkeys/opencast-deb.key | apt-key add -
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add -
RUN curl -fsSL https://artifacts.crowdin.com/repo/GPG-KEY-crowdin | apt-key add -

COPY opencast.list /etc/apt/sources.list.d
COPY opencast-test.list /etc/apt/sources.list.d
COPY nodesource.list /etc/apt/sources.list.d
COPY crowdin.list /etc/apt/sources.list.d

#JDK8 is not present in buster, but lives in unstable instead
COPY debian-unstable.list /etc/apt/sources.list.d/
COPY debian-testing.list /etc/apt/sources.list.d/
#This file prevents the whole system from upgrading due to the above configuration
COPY 99defaultrelease /etc/apt/apt.conf.d/

COPY aws-config /builder/.aws/config

RUN apt-get update && \
    apt-get dist-upgrade -y

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
#        openjdk-8-jre \
	openjdk-11-jre \
     # Build deps
        openssh-client \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
#        openjdk-8-jdk \
        openjdk-11-jdk \
        firefox-esr \
     # Doc deps
     ## Python deps
        gcc \
        python3-dev \
        python3-pip \
     ## Packages for building docs
        libyaml-dev \
        nodejs \
     ## For SQL script testing
        mariadb-client \
     # Package building deps
        dpkg-dev \
        debhelper \
        devscripts \
        dh-exec \
     # Repository generator
        mini-dinstall \
     # Database test script use
        bc \
     # Crowdin
        crowdin3 && \
     apt-get clean

RUN apt-get install -y --no-install-recommends -t unstable gcc-8-base && apt-get clean
RUN apt-get install -y --no-install-recommends -t unstable openjdk-8-jre && apt-get clean
RUN apt-get install -y --no-install-recommends -t unstable openjdk-8-jdk && apt-get clean

RUN update-java-alternatives -s java-1.8.0-openjdk-amd64

RUN python3 -m pip --no-cache-dir install --upgrade pip
RUN python3 -m pip --no-cache-dir install --upgrade setuptools
    # Markdown doc generation bits
RUN python3 -m pip --no-cache-dir install mkdocs markdown_inline_graphviz_extension mkdocs-windmill six
    # Ansible deploy bits
RUN python3 -m pip --no-cache-dir install ansible paramiko
    # Buildbot s3 deploy bits
RUN python3 -m pip --no-cache-dir install awscli

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
RUN python3 -m pip --no-cache-dir install buildbot-worker==2.8.3

