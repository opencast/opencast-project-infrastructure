FROM debian:stretch
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

COPY ffmpeg*.deb /root/

RUN echo 'Acquire::http::Proxy "http://repo:3142";' > /etc/apt/apt.conf.d/01proxy && \
    apt-get update && \
    apt-get install -y \
        software-properties-common \
        apt-transport-https \
        curl \
        gnupg && \
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
        openjdk-8-jdk && \
     dpkg -i /root/*.deb && \
     rm -f /root/*.deb && \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/*
