FROM debian:9
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y apt-transport-https gnupg curl && \
    curl https://pkg.opencast.org/gpgkeys/opencast-deb.key | apt-key add -

COPY opencast.list /etc/apt/sources.list.d

RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y \
        bash \
        locales \
     # Run deps
        tesseract-ocr \
#        tesseract-ocr-eng \
        netcat \
        synfig \
        sox \
        hunspell \
#        hunspell-en-us \
        ffmpeg-dist \
        openjdk-8-jre && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

