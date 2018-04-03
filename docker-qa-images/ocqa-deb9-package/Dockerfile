FROM greglogan/ocqa-deb9-doc
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y \
     # Package building deps
        dpkg-dev \
        debhelper \
        dh-exec \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/*
