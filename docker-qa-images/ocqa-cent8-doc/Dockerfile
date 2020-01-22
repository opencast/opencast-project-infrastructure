FROM greglogan/ocqa-cent8-build:v2.6.0
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY nodesource-el8.repo /etc/yum.repos.d/
COPY NODESOURCE-GPG-SIGNING-KEY-EL /etc/pki/rpm-gpg/

RUN yum install -y \
     # Python deps
        python36 \
        python36-devel \
        python3-pip \
     # Packages for building docs
        nodejs \
     # For SQL script testing
        mysql && \
    yum clean all && \
    pip3.6 install mkdocs markdown_inline_graphviz_extension mkdocs-windmill

