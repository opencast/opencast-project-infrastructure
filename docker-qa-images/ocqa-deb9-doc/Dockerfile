FROM greglogan/ocqa-deb9-build
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN apt-get update && \
    apt-get install -y \
        gnupg \
        software-properties-common \
        apt-transport-https && \
    add-apt-repository \
        'deb https://deb.nodesource.com/node_8.x stretch main' && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
    apt-get update && \
    # Build deps
    apt-get install -y \
     # Python deps
        python-pip \
     # Packages for building docs
        libyaml-dev \
        nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install mkdocs

