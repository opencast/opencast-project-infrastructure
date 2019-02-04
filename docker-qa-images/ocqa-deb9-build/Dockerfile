FROM greglogan/ocqa-deb9-run:v2.0.0
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

# Build deps
RUN apt-get update && \
    apt-get install -y \
        tar gzip bzip2 unzip \
        git \
        maven \
        curl wget \
        openjdk-8-jdk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash -d /builder builder && \
    mkdir /builder/.ssh && \
    chown -R builder:builder /builder

