FROM centos:7
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY *.repo /etc/yum.repos.d/

RUN sed -i '/override_install_langs/d' /etc/yum.conf && \
    yum update -y && \
    yum install -y epel-release && \
    yum install -y \
        bash \
     # Run deps
        tesseract \
#        tesseract-langpack-deu \
        nmap-ncat \
        synfig \
        ffmpeg \
        sox \
        hunspell \
#        hunspell-en \
        java-1.8.0-openjdk && \
    yum clean all

