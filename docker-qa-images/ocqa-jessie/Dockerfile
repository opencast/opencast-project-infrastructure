FROM debian:jessie
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#COPY gregorydlogan.oc-codesign.gpg.key /root/gregorydlogan.oc-codesign.gpg.key
COPY ffmpeg_3.2.2-1_amd64.deb /root/ffmpeg_3.2.2-1_amd64.deb

RUN apt-get update \
#   TODO: Get this pulling from the repo rather than relying on build-time COPYs
#    && apt-key add /root/gregorydlogan.oc-codesign.gpg.key \
    && apt-get install -y \
        software-properties-common \
#        apt-transport-https \
    && add-apt-repository \
        'deb http://httpredir.debian.org/debian/ jessie-backports main contrib non-free' \
#    && add-apt-repository \
#	"deb https://$OC_REPO_USER:$OC_REPO_PASS@pkg.opencast.org/debian jessie testing" \
    # Build deps
    && apt-get update \
    && apt-get dist-upgrade \
    && apt-get install -y \
        sudo \
        tar gzip bzip2 unzip \
        git \
        openjdk-7-jdk \
     # Maven from backports because Jessie ships with 3.0.5
     && apt-get install -y \
        -t jessie-backports maven \
     # Run deps
     && apt-get install -y \
#        ffmpeg \
        tesseract-ocr \
        netcat \
        hunspell \
     # Package building deps
     && apt-get install -y \
        dpkg-dev \
        debhelper \
        dh-exec \
     && dpkg -i /root/ffmpeg_3.2.2-1_amd64.deb
     # Remove the repo
#     && add-apt-repository -r \
#	"deb https://$OC_REPO_USER:$OC_REPO_PASS@pkg.opencast.org/debian jessie testing"
