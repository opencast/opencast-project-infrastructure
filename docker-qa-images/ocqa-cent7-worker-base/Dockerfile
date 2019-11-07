FROM greglogan/ocqa-cent7-deploy:v2.5.0
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Adapted from https://github.com/buildbot/buildbot/blob/v1.7.0/worker/Dockerfile

COPY buildbot.tac /builder/buildbot.tac
COPY crowdin.repo /etc/yum.repos.d/crowdin.repo
COPY aws-config /builder/.aws/config

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init && \
     rpm --import https://artifacts.crowdin.com/repo/GPG-KEY-crowdin && \
     yum install -y \
         #Bits for buildbot worker
         gcc \
         openssl-devel \
         #Crowdin
         crowdin \
         # bc for the database test script
         bc && \
     # Install required python packages, and twisted
     pip3.6 install --upgrade pip setuptools && \
     pip3.6 install awscli buildbot-worker==2.5.0


