FROM quay.io/centos/centos:stream9 AS base

#Needed to work around pip bug: https://githubmemory.com/repo/pypa/pip/issues/10219
ARG LANG=en_US.UTF-8
ARG LC_ALL=en_US.UTF-8
ARG VERSION=unknown
ARG BUILD_DATE=unknown


LABEL org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.title="Opencast QA CentOS Stream 9 Image" \
      org.opencontainers.image.description="Opencast QA image based on a CentOS Stream 9 environment" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="Opencast" \
      org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.url="https://github.com/opencast/opencast-project-infrastructure/docker-qa-images" \
      org.opencontainers.image.source="https://github.com/opencast/opencast-project-infrastructure" \
      org.opencontainers.image.created="${BUILD_DATE}"

COPY repos/* /etc/yum.repos.d/
COPY keys/* /etc/pki/rpm-gpg/

COPY aws-config /builder/.aws/config

RUN sed -i '/override_install_langs/d' /etc/yum.conf

# Install epel and sudo (for UID/GID mod)
RUN yum install -y \
        epel-release \
        sudo \
        # dnf needed for the docker bits later
        dnf \
        dnf-plugins-core

RUN dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

RUN yum install -y \
        bash \
     # Run deps
        tesseract \
        nmap-ncat \
        sox \
        hunspell \
     # Build deps
        openssh-clients \
        tar gzip bzip2 unzip \
        git \
       #curl is provided in the image and breaks the install if you try and update it again
       #curl \
        wget \
        firefox && \
    yum clean all

#Requires appimage, which doesn't work in Docker.
#and appimagetool's extraction is not yet implemented, despite being documented as the 'solution' here
#RUN curl --silent "https://api.github.com/repos/synfig/synfig/releases/latest" | \
#    grep "browser_download_url.*linux64*" | \
#    cut -d : -f 2,3 | tr -d \" | wget -qi - -O /usr/bin/synfig && \
#    chmod 755 /usr/bin/synfig

RUN yum install -y \
     # Doc deps
     ## Python deps for markdown
        python3 \
        python3-devel \
        python3-pip && \
    yum clean all

RUN yum install -y \
     # Package building deps
        createrepo \
        rpmdevtools \
        rpmlint \
        yum-utils \
        rpm-sign \
        s3fs-fuse \
     # Bits for buildbot worker
        gcc \
        openssl-devel \
     # Crowdin
        crowdin && \
    yum clean all

RUN dnf module install -y nodejs:18

# The base CentOS image strips the locales out, this reinstalls them
RUN yum install -y \
        glibc-langpack-en \
        glibc-langpack-de \
        glibc-langpack-es \
        glibc-langpack-fr && \
    yum clean all

RUN python3 -m pip --no-cache-dir install --upgrade pip setuptools
    # Ansible deploy bits
RUN python3 -m pip --no-cache-dir install ansible paramiko
    # Buildbot s3 deploy bits
RUN python3 -m pip --no-cache-dir install requests urllib3
RUN python3 -m pip --no-cache-dir install awscli
    # Vosk and vosk-cli
RUN python3 -m pip --no-cache-dir install vosk vosk-cli webvtt-py && \
    mkdir -p /usr/share/vosk/models && \
    wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -O /usr/share/vosk/models/vosk-model-small-en-us-0.15.zip && \
    unzip /usr/share/vosk/models/vosk-model-small-en-us-0.15.zip -d /usr/share/vosk/models/ && \
    rm -f /usr/share/vosk/models/vosk-model-small-en-us-0.15.zip
#NB: This adds about 3GB to the image, even without a model
#    #Whisper, except without models
##RUN python3 -m pip --no-cache-dir install openai-whisper

#Install bits only needed for docker setup
RUN yum install -y docker-ce-cli && \
    yum clean all && \
    groupdel docker

    # Test runs produce a great quantity of dead grandchild processes.  In a
    # non-docker environment, these are automatically reaped by init (process 1),
    # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

#Allow buildbot to install packages (ffmpeg) later
RUN echo "buildbot ALL = (root) NOPASSWD : /usr/bin/apt-get, /usr/bin/yum, /usr/local/bin/dumb-init, /bin/sed" > /etc/sudoers.d/buildbot

COPY buildbot.tac /builder/buildbot.tac
    # Install required python packages, and twisted
RUN python3 -m pip --no-cache-dir install buildbot-worker==${VERSION}

COPY install-ffmpeg.sh /builder/install-ffmpeg.sh
RUN chmod 755 /builder/install-ffmpeg.sh


FROM base AS jdk11

RUN yum install -y \
        java-11-openjdk \
        java-11-openjdk-devel && \
    #Do this after to prevent installing the default jdk
    yum install -y \
        maven

COPY opencast.repo /etc/yum.repos.d/opencast.repo


FROM base AS jdk17

RUN yum install -y \
        java-17-openjdk \
        java-17-openjdk-devel && \
    #Do this after to prevent installing the default jdk
    yum install -y \
        maven

COPY opencast.repo /etc/yum.repos.d/opencast.repo


FROM base AS jdk21

RUN yum install -y \
        java-21-openjdk \
        java-21-openjdk-devel && \
    #Do this after to prevent installing the default jdk
    yum install -y \
        maven

COPY opencast.repo /etc/yum.repos.d/opencast.repo
