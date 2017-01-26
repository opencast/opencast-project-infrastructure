FROM debian:jessie
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY opencast-ffmpeg_3.2.2-1_amd64.deb /root/opencast-ffmpeg_3.2.2-1_amd64.deb

RUN apt-get update \
    && apt-get install -y \
        software-properties-common \
    && add-apt-repository \
        'deb http://httpredir.debian.org/debian/ jessie-backports main contrib non-free' \
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
        tesseract-ocr \
        netcat \
        hunspell \
     && dpkg -i /root/opencast-ffmpeg_3.2.2-1_amd64.deb
