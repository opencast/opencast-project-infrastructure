FROM greglogan/ocqa-cent8-build:v2.5.0
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN curl -sL -o '/tmp/nodesource-release-el7-1.noarch.rpm' 'https://rpm.nodesource.com/pub_8.x/el/7/x86_64/nodesource-release-el7-1.noarch.rpm' && \
    rpm -i --nosignature --force '/tmp/nodesource-release-el7-1.noarch.rpm' && \
    rm -f '/tmp/nodesource-release-el7-1.noarch.rpm' && \
    # Build deps
    yum install -y \
     # Python deps
        python36 \
        python36-devel \
        python36-pip \
     # Packages for building docs
        nodejs \
     # For SQL script testing
        mysql && \
    yum clean all && \
    pip3.6 install --upgrade pip setuptools && \
    pip3.6 install mkdocs markdown_inline_graphviz_extension mkdocs-windmill

