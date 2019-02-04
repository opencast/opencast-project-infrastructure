FROM greglogan/ocqa-cent7-package:v2.0.0
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Adapted from https://github.com/buildbot/buildbot/blob/v1.7.0/worker/Dockerfile

COPY . /usr/src/buildbot-worker
COPY docker/buildbot.tac /builder/buildbot.tac
COPY crowdin.repo /etc/yum.repos.d/crowdin.repo

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
     chmod +x /usr/local/bin/dumb-init && \
     rpm --import https://artifacts.crowdin.com/repo/GPG-KEY-crowdin && \
     yum install -y \
         #Bits for buildbot worker
         gcc \
         python36-devel \
         #Crowdin
         crowdin \
         # bc for the database test script
         bc && \
     # Install required python packages, and twisted
     pip3 install 'twisted[tls]' && \
     pip3 install /usr/src/buildbot-worker

USER builder

WORKDIR /builder

CMD ["/usr/local/bin/dumb-init", "twistd", "--pidfile=", "-ny", "buildbot.tac"]
