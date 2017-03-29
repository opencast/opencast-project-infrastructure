FROM debian:jessie
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY gregorydlogan.oc-codesign.gpg.key /root/gregorydlogan.oc-codesign.gpg.key

RUN apt-get update \
    && apt-key add /root/gregorydlogan.oc-codesign.gpg.key \
    && apt-get install -y \
        software-properties-common \
    && add-apt-repository \
        'deb http://httpredir.debian.org/debian/ jessie-backports main contrib non-free' \
	&& add-apt-repository \
	'deb http://oc-cache.usask.ca/repo/ jessie main' \
    # Build deps
    && apt-get update \
    && apt-get install -y \
        sudo \
        tar gzip bzip2 unzip \
        git \
        openjdk-7-jdk \
     # Maven from backports because Jessie ships with 3.0.5
     && apt-get install -y \
        -t jessie-backports maven \
     # Run deps
     && apt-get install -y \
        opencast-ffmpeg \
        tesseract-ocr \
        netcat \
        hunspell \
     # Package building deps
     && apt-get isntall -y \
        dpkg-dev \
        debhelper \
        dh-exec
