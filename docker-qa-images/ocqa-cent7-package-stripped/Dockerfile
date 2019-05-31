FROM centos:7
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY buildbot.tac /builder/buildbot.tac

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y \
        bash \
        openssh-clients \
     # Package building deps
        createrepo \
        rpmdevtools \
        rpmlint \
        yum-utils \
        rpm-sign && \
     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
    curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
    chmod +x /usr/local/bin/dumb-init && \
    yum install -y \
         #Bits for buildbot worker
         gcc \
         python36 \
         python36-devel \
         python36-pip \
         openssl-devel \
         # bc for the database test script
         bc && \
     # Install required python packages, and twisted
    pip3.6 install --upgrade pip setuptools && \
    pip3.6 install buildbot-worker==2.3.1 && \
    yum clean all

