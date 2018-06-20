FROM greglogan/ocqa-cent7-package
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Adapted from https://github.com/buildbot/buildbot/blob/v1.1.0/worker/Dockerfile

COPY . /usr/src/buildbot-worker
COPY docker/buildbot.tac /builder/buildbot.tac

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.1.3/dumb-init_1.1.3_amd64 && \
     chmod +x /usr/local/bin/dumb-init && \
     # Install required python packages, and twisted
     pip install 'twisted[tls]' && \
     pip install /usr/src/buildbot-worker

#wget --quiet https://artifacts.crowdin.com/repo/deb/crowdin.deb
COPY crowdin.deb /root/crowdin.deb

RUN dpkg -i /root/crowdin.deb && \
    rm -f /root/crowdin.deb

USER builder

WORKDIR /builder

CMD ["/usr/local/bin/dumb-init", "twistd", "-ny", "buildbot.tac"]
