FROM greglogan/ocqa-cent7-run:v2.3.1
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY *.rpm /root/

# Build deps
RUN yum install -y \
        tar gzip bzip2 unzip \
        git \
#        maven \
        curl wget \
        java-1.8.0-openjdk-devel && \
    yum install -y /root/*.rpm && \
    rm -f /root/*.rpm && \
    yum clean all

