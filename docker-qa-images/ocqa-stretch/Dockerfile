FROM debian:stretch
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Adapted from https://github.com/buildbot/buildbot/blob/v1.1.0/worker/Dockerfile

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

RUN echo 'Acquire::http::Proxy "http://repo:3142";' > /etc/apt/apt.conf.d/01proxy && \
    apt-get update && \
    apt-get install -y \
        software-properties-common \
        apt-transport-https \
        curl \
        gnupg && \
    add-apt-repository \
        'deb https://deb.nodesource.com/node_8.x stretch main' && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
    # Build deps
    apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y \
        sudo \
        tar gzip bzip2 unzip \
        git \
     # Run deps
        tesseract-ocr \
        netcat \
        hunspell \
        synfig \
        maven \
        openjdk-8-jdk \
     # Package building deps
        dpkg-dev \
        debhelper \
        dh-exec \
     # Python deps
        python-dev \
        python-pip \
     # Packages for building docs
        libyaml-dev \
        nodejs \
     # Packages for buildbot-worker
        build-essential \
        git \
        subversion \
        libffi-dev \
        libssl-dev && \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/* && \
     pip install --upgrade pip virtualenv setuptools && \
     pip install mkdocs

COPY . /usr/src/buildbot-worker
COPY docker/buildbot.tac /buildbot/buildbot.tac

     # Test runs produce a great quantity of dead grandchild processes.  In a
     # non-docker environment, these are automatically reaped by init (process 1),
     # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN  curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.1.3/dumb-init_1.1.3_amd64 && \
     chmod +x /usr/local/bin/dumb-init && \
     # Install required python packages, and twisted
     pip install 'twisted[tls]' && \
     pip install /usr/src/buildbot-worker && \
     useradd -ms /bin/bash buildbot && chown -R buildbot /buildbot

USER buildbot

WORKDIR /buildbot

CMD ["/usr/local/bin/dumb-init", "twistd", "-ny", "buildbot.tac"]
