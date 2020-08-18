FROM centos:7
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY opencast.repo /etc/yum.repos.d/
COPY opencast-testing.repo /etc/yum.repos.d/
COPY nodesource-el7.repo /etc/yum.repos.d/
COPY crowdin.repo /etc/yum.repos.d/

COPY NODESOURCE-GPG-SIGNING-KEY-EL /etc/pki/rpm-gpg/
COPY GPG-KEY-crowdin /etc/pki/rpm-gpg/

COPY aws-config /builder/.aws/config

RUN sed -i '/override_install_langs/d' /etc/yum.conf

# Install the dependencies
RUN yum install -y epel-release &&\
    yum update -y && \
    yum clean all

RUN yum install -y \
        bash \
     # Run deps
        tesseract \
        nmap-ncat \
        synfig \
        ffmpeg \
        sox \
        hunspell \
        java-1.8.0-openjdk \
        java-11-openjdk \
     # Build deps
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        java-1.8.0-openjdk-devel \
        java-11-openjdk-devel \
        firefox \
     # Doc deps
     ## Python deps for markdown
        python36 \
        python36-devel \
        python36-pip \
     ## Packages for building docs
        nodejs \
     ## For SQL script testing
        mysql \
     # Package building deps
        createrepo \
        rpmdevtools \
        rpmlint \
        yum-utils \
        rpm-sign \
     # Bits for buildbot worker
         gcc \
         openssl-devel \
     # Crowdin
         crowdin \
     # bc for the database test script
         bc && \
    yum clean all

RUN alternatives --set java java-1.8.0-openjdk.x86_64
RUN alternatives --set javac java-1.8.0-openjdk.x86_64

# The base CentOS image strips the locales out, this reinstalls them
RUN yum reinstall -y glibc-common

    # Markdown doc generation bits
RUN pip3.6 install --no-cache-dir mkdocs markdown_inline_graphviz_extension mkdocs-windmill
    # Ansible deploy bits
RUN pip3.6 install --no-cache-dir ansible paramiko
    # Buildbot s3 deploy bits
RUN pip3.6 install --no-cache-dir awscli

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

COPY buildbot.tac /builder/buildbot.tac
    # Install required python packages, and twisted
RUN pip3.6 install --no-cache-dir buildbot-worker==2.8.2

