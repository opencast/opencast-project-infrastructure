FROM debian:10
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY buildbot.tac /builder/buildbot.tac

RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y \
        bash \
     # Python deps
        python3-pip \
        python-pip \
     # Package building deps
        dpkg-dev \
        debhelper \
        devscripts \
        dh-exec \
     # Repository generator
        mini-dinstall \
     # bc for the database test script
        bc && \
     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
    curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
    chmod +x /usr/local/bin/dumb-init && \
     # Install required python packages, and twisted
    pip3 install buildbot-worker==2.6.0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

