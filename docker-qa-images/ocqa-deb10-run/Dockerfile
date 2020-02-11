FROM debian:10
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y apt-transport-https gnupg curl && \
    curl https://pkg.opencast.org/gpgkeys/opencast-deb.key | apt-key add -

COPY opencast.list /etc/apt/sources.list.d/
#JDK8 is not present in buster, but lives in unstable instead
COPY debian-unstable.list /etc/apt/sources.list.d/
#This file prevents the whole system from upgrading due to the above configuration
COPY 99defaultrelease /etc/apt/apt.conf.d/

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
        ffmpeg-dist &&\
    apt-get install -y -t unstable openjdk-8-jre && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

