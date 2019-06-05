FROM greglogan/ocqa-deb9-package:v2.3.1
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN add-apt-repository \
    'deb http://ppa.launchpad.net/ansible/ansible/ubuntu trusty main' && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 93C4A3FD7BB9C367 && \
    apt-get update && \
    apt-get install -y \
     ansible && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

