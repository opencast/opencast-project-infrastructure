FROM debian:jessie
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN echo 'Acquire::http::Proxy "http://apt-cacher:3142";' > /etc/apt/apt.conf.d/01proxy \
    && apt-get update \
    && apt-get install -y \
        software-properties-common \
        apt-transport-https \
        wget \
    && add-apt-repository \
        'deb http://deb.debian.org/debian jessie-backports main contrib non-free' \
    && add-apt-repository \
        'deb https://deb.nodesource.com/node_8.x jessie main' \
    && wget -qO- https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
    # Build deps
    && apt-get update \
    && apt-get dist-upgrade \
    && apt-get install -y \
        sudo \
        tar gzip bzip2 unzip \
        git \
     # Run deps
        tesseract-ocr \
        netcat \
        hunspell \
        synfig \
     # Package building deps
        dpkg-dev \
        debhelper \
        dh-exec \
     # Packages for building docs
        python-dev \
        python-pip \
        libyaml-dev \
        nodejs \
     # Maven from backports because Jessie ships with 3.0.5
     && apt-get install -y \
        -t jessie-backports maven \
        openjdk-8-jdk \
     && pip install mkdocs \
     && apt-get clean
