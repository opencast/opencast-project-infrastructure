FROM greglogan/ocqa-deb9-build
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN add-apt-repository \
        'deb https://deb.nodesource.com/node_8.x stretch main' && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
    apt-get update && \
    apt-get dist-upgrade -y && \
    # Build deps
    apt-get install -y \
     # Python deps
        python-dev \
        python-pip \
     # Packages for building docs
        libyaml-dev \
        nodejs \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/* && \
     pip install --upgrade pip virtualenv setuptools && \
     pip install mkdocs
