FROM debian:jessie-slim
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN apt-get update \
    && apt-get install -y \
        software-properties-common \
        apt-transport-https \
        wget
    && wget -qO - https://pkg.opencast.org/gpgkeys/opencast-deb.key | apt-key add - \
    && add-apt-repository \
        'deb http://deb.debian.org/debian jessie-backports main contrib non-free' \
    # Build deps
    && apt-get update \
    && apt-get dist-upgrade \
    && apt-get install -y \
        sudo \
        tar gzip bzip2 unzip \
        git \
     # Maven from backports because Jessie ships with 3.0.5
     && apt-get install -y \
        -t jessie-backports maven \
        openjdk-8-jdk \
     # Run deps
     && apt-get install -y \
        tesseract-ocr \
        netcat \
        hunspell \
     # Package building deps
     && apt-get install -y \
        dpkg-dev \
        debhelper \
        dh-exec \
     && apt-get clean
