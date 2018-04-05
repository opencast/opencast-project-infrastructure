FROM greglogan/ocqa-deb9-package
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Adapted from https://github.com/buildbot/buildbot/blob/v1.1.0/worker/Dockerfile

RUN apt-get update && \
    apt-get dist-upgrade -y && \
     #Create the buildbot user, add it to sudoers so that we can install ffmpeg etc at runtime
     useradd -ms /bin/bash -d /buildbot buildbot && \
     mkdir /buildbot/.ssh && \
     chown -R buildbot /buildbot

COPY . /usr/src/buildbot-worker
COPY docker/buildbot.tac /buildbot/buildbot.tac

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.1.3/dumb-init_1.1.3_amd64 && \
     chmod +x /usr/local/bin/dumb-init && \
     # Install required python packages, and twisted
     pip install 'twisted[tls]' && \
     pip install /usr/src/buildbot-worker

USER buildbot

WORKDIR /buildbot

CMD ["/usr/local/bin/dumb-init", "twistd", "-ny", "buildbot.tac"]
