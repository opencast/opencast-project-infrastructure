FROM greglogan/ocqa-cent7-build
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN curl -sL -o '/tmp/nodesource-release-el7-1.noarch.rpm' 'https://rpm.nodesource.com/pub_8.x/el/7/x86_64/nodesource-release-el7-1.noarch.rpm' && \
    rpm -i --nosignature --force '/tmp/nodesource-release-el7-1.noarch.rpm' && \
    rm -f '/tmp/nodesource-release-el7-1.noarch.rpm' && \
    # Build deps
    yum install -y \
     # Python deps
        python-pip \
     # Packages for building docs
        nodejs \
     # For SQL script testing
        mysql && \
    yum clean all && \
    pip install mkdocs

