FROM centos:8
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY opencast.repo /etc/yum.repos.d/
COPY opencast-testing.repo /etc/yum.repos.d/
COPY nodesource-el8.repo /etc/yum.repos.d/
COPY crowdin.repo /etc/yum.repos.d/

COPY keys/* /etc/pki/rpm-gpg/

COPY aws-config /builder/.aws/config

RUN sed -i '/override_install_langs/d' /etc/yum.conf

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2021-04-16

# Install the dependencies
RUN yum install -y epel-release &&\
    yum install -y \
        bash \
     # Run deps
        tesseract \
        nmap-ncat \
# not built yet due to lack of time
#        synfig \
        ffmpeg \
# not built yet due to dependency issues
#        sox \
        hunspell \
        java-1.8.0-openjdk \
        java-11-openjdk \
        java-13-openjdk \
     # Build deps
        openssh-clients \
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
        python3-pip \
     ## Packages for building docs
        nodejs \
     ## For SQL script testing
        mysql \
     # Package building deps
     # Moved below, causes yum to crash and corrupt its db if it's here
#        createrepo \
#        rpmdevtools \
#        rpmlint \
#        yum-utils \
#        rpm-sign \
     # Bits for buildbot worker
         gcc \
         openssl-devel \
     # Crowdin
         crowdin \
     # bc for the database test script
         bc

RUN yum install -y \
        createrepo \
        rpmdevtools \
        rpmlint \
        yum-utils \
        rpm-sign

RUN alternatives --set java java-1.8.0-openjdk.x86_64
RUN alternatives --set javac java-1.8.0-openjdk.x86_64

# The base CentOS image strips the locales out, this reinstalls them
RUN yum install -y glibc-langpack-en glibc-langpack-de glibc-langpack-es glibc-langpack-fr

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
RUN python3 -m pip --no-cache-dir install buildbot-worker==3.1.0

