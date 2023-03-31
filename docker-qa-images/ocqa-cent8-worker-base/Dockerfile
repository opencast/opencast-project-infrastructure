FROM quay.io/centos/centos:stream8

#Needed to work around pip bug: https://githubmemory.com/repo/pypa/pip/issues/10219
ARG LANG=en_US.UTF-8
ARG LC_ALL=en_US.UTF-8
ARG VERSION=unknown
ARG BUILD_DATE=unknown


LABEL maintainer="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.title="Opencast QA CentOS Stream 8 Image" \
      org.opencontainers.image.description="Opencast QA image based on a CentOS Stream 8 environment" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="Opencast" \
      org.opencontainers.image.authors="Greg Logan <gregorydlogan@gmail.com>" \
      org.opencontainers.image.url="https://github.com/opencast/opencast-project-infrastructure/docker-qa-images" \
      org.opencontainers.image.source="https://github.com/opencast/opencast-project-infrastructure" \
      org.opencontainers.image.created="${BUILD_DATE}"

COPY repos/* /etc/yum.repos.d/
COPY keys/* /etc/pki/rpm-gpg/

COPY aws-config /builder/.aws/config
COPY install-ffmpeg.sh /builder/install-ffmpeg.sh

RUN chmod 755 /builder/install-ffmpeg.sh

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
        java-11-openjdk \
        java-17-openjdk \
     # Build deps
        openssh-clients \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        java-11-openjdk-devel \
        java-17-openjdk-devel \
        firefox && \
    yum clean all

RUN curl --silent "https://api.github.com/repos/synfig/synfig/releases/latest" | \
    grep "browser_download_url.*linux64*" | \
    cut -d : -f 2,3 | tr -d \" | wget -qi - -O /usr/bin/synfig && \
    chmod 755 /usr/bin/synfig

RUN yum install -y \
     # Doc deps
     ## Python deps for markdown
        python36 \
        python36-devel \
        python3-pip && \
    yum clean all

RUN dnf module install -y nodejs:16

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

RUN alternatives --set java java-11-openjdk.x86_64
RUN alternatives --set javac java-11-openjdk.x86_64

# The base CentOS image strips the locales out, this reinstalls them
RUN yum install -y \
        glibc-langpack-en \
        glibc-langpack-de \
        glibc-langpack-es \
        glibc-langpack-fr && \
    yum clean all

RUN python3 -m pip --no-cache-dir install --upgrade pip
RUN python3 -m pip --no-cache-dir install --upgrade setuptools
    # Ansible deploy bits
RUN python3 -m pip --no-cache-dir install ansible paramiko
    # Buildbot s3 deploy bits
RUN python3 -m pip --no-cache-dir install --upgrade requests urllib3
RUN python3 -m pip --no-cache-dir install awscli
    # Vosk, notably without any language models
RUN python3 -m pip --no-cache-dir install vosk webvtt-py

#Install bits only needed for docker setup
RUN yum install -y docker-ce-cli && \
    yum clean all && \
    groupdel docker

    # Test runs produce a great quantity of dead grandchild processes.  In a
    # non-docker environment, these are automatically reaped by init (process 1),
    # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

COPY opencast.repo /etc/yum.repos.d/opencast.repo
#Allow buildbot to install packages (ffmpeg) later
RUN echo "buildbot ALL = (root) NOPASSWD : /usr/bin/apt-get, /usr/bin/yum, /usr/local/bin/dumb-init, /bin/sed" > /etc/sudoers.d/buildbot

COPY buildbot.tac /builder/buildbot.tac
    # Install required python packages, and twisted
RUN python3 -m pip --no-cache-dir install future buildbot-worker==${VERSION}
