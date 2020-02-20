FROM greglogan/ocqa-deb10-doc:latest
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN apt-get update && \
    apt-get install -y \
     # Package building deps
        dpkg-dev \
        devscripts \
     # Repository generator
        mini-dinstall && \
    apt-get install -y -t unstable \
        debhelper \
        dh-exec && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

