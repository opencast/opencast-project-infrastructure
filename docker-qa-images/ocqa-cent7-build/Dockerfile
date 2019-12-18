FROM greglogan/ocqa-cent7-run:v2.5.1
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# Build deps
RUN yum install -y \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        java-1.8.0-openjdk-devel && \
    yum clean all

