FROM centos:7
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#Needed to work around pip bug: https://githubmemory.com/repo/pypa/pip/issues/10219
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

COPY opencast.repo /etc/yum.repos.d/
COPY opencast-testing.repo /etc/yum.repos.d/
COPY nodesource-el7.repo /etc/yum.repos.d/
COPY crowdin.repo /etc/yum.repos.d/

COPY keys/* /etc/pki/rpm-gpg/

COPY aws-config /builder/.aws/config

RUN sed -i '/override_install_langs/d' /etc/yum.conf

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2021-08-23

# Install the dependencies
RUN yum install -y epel-release

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
        java-17-openjdk \
     # Build deps
        openssh-clients \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        java-1.8.0-openjdk-devel \
        java-11-openjdk-devel \
        java-17-openjdk-devel \
        firefox && \
    yum clean all

RUN yum install -y \
     # Doc deps
     ## Python deps for markdown
        python36 \
        python36-devel \
        python36-pip \
     ## Packages for building docs
        nodejs \
     ## For SQL script testing
        mysql && \
    yum clean all

RUN yum install -y \
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
     # jq for maintenance
         jq && \
    yum clean all

RUN alternatives --set java java-11-openjdk.x86_64
RUN alternatives --set javac java-11-openjdk.x86_64

RUN python3 -m pip --no-cache-dir install --upgrade pip
RUN python3 -m pip --no-cache-dir install --upgrade setuptools
    # Ansible deploy bits
RUN python3 -m pip --no-cache-dir install ansible paramiko
    # Buildbot s3 deploy bits
RUN python3 -m pip --no-cache-dir install awscli

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init

COPY buildbot.tac /builder/buildbot.tac
    # Install required python packages, and twisted
RUN python3 -m pip --no-cache-dir install buildbot-worker==3.3.0

