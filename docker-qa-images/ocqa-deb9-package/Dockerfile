FROM greglogan/ocqa-deb9-doc
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN apt-get update && \
    apt-get install -y \
     # Package building deps
        dpkg-dev \
        debhelper \
        devscripts \
        dh-exec \
     # Repository generator
        mini-dinstall && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

