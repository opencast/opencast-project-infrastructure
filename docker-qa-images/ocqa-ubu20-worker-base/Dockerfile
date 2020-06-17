FROM ubuntu:20.04
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y apt-transport-https gnupg curl && \
    apt-get clean

RUN curl -fsSL https://pkg.opencast.org/gpgkeys/opencast-deb.key | apt-key add -
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add -
RUN curl -fsSL https://artifacts.crowdin.com/repo/GPG-KEY-crowdin | apt-key add -

COPY opencast.list /etc/apt/sources.list.d
COPY opencast-test.list /etc/apt/sources.list.d
COPY nodesource.list /etc/apt/sources.list.d
COPY crowdin.list /etc/apt/sources.list.d

COPY aws-config /builder/.aws/config

RUN apt-get update && \
    apt-get dist-upgrade -y

RUN apt-get install -y \
        bash \
        locales \
     # Run deps
        tesseract-ocr \
        netcat \
        synfig \
        sox \
        hunspell \
        ffmpeg-dist \
        openjdk-8-jre \
     # Build deps
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        openjdk-8-jdk \
        firefox \
     # Doc deps
     ## Python deps
        python3-pip \
     ## Packages for building docs
        libyaml-dev \
        nodejs \
     ## For SQL script testsing
        mysql-client \
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

    # Markdown doc generation bits
RUN pip3 install --no-cache-dir mkdocs markdown_inline_graphviz_extension mkdocs-windmill
    # Ansible deploy bits
RUN pip3 install --no-cache-dir ansible paramiko
    # Buildbot s3 deploy bits
RUN pip3 install --no-cache-dir awscli

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

COPY buildbot.tac /builder/buildbot.tac
     # Install required python packages, and twisted
RUN pip3 install --no-cache-dir buildbot-worker==2.8.2

