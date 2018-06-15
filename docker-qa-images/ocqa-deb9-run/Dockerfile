FROM debian:stretch
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

COPY ffmpeg*.deb /root/

RUN echo 'Acquire::http::Proxy "http://repo:3142";' > /etc/apt/apt.conf.d/01proxy && \
    apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y \
     # Run deps
        tesseract-ocr \
        tesseract-ocr-eng \
        netcat \
        hunspell \
        synfig \
        sox \
        hunspell \
        hunspell-en-us \
        openjdk-8-jre && \
    dpkg -i /root/*.deb && \
    rm -f /root/*.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

