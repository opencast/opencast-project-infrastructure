FROM greglogan/ocqa-cent7-run
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Build deps
RUN yum install -y \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        java-1.8.0-openjdk-devel && \
    yum clean all && \
    useradd -ms /bin/bash -d /builder builder && \
    mkdir /builder/.ssh && \
    chown -R builder:builder /builder

