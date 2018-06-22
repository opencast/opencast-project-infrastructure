FROM greglogan/ocqa-cent7-run
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY *.rpm /root/

# Build deps
RUN yum install z-y \
        tar gzip bzip2 unzip \
        git \
#        maven \
        curl wget \
        java-1.8.0-openjdk-devel && \
    yum install /root/*.rpm && \
    rm -f /root/*.rpm && \
    yum clean all && \
    useradd -ms /bin/bash -d /builder builder && \
    mkdir /builder/.ssh && \
    chown -R builder:builder /builder

