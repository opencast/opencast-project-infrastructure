FROM greglogan/ocqa-deb9-deploy:v2.5.0
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Adapted from https://github.com/buildbot/buildbot/blob/v1.7.0/worker/Dockerfile

COPY buildbot.tac /builder/buildbot.tac
COPY aws-config /builder/.aws/config

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init && \
     # Install required python packages, and twisted
     pip3 install awscli buildbot-worker==2.5.0 && \
     # bc for the database test script
     apt-get update && \
     apt-get install bc && \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/*

ADD https://artifacts.crowdin.com/repo/deb/crowdin.deb /root/crowdin.deb

RUN dpkg -i /root/crowdin.deb && \
    rm -f /root/crowdin.deb

