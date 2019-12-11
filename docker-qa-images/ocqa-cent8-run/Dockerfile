FROM centos:8
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY *.rpm /root/

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y \
        bash \
     # Run deps
        tesseract \
        tesseract-langpack-deu \
        nmap-ncat \
#       synfig \
#       ffmpeg \
        sox \
        hunspell \
        hunspell-en \
        java-1.8.0-openjdk && \
    yum install -y /root/*.rpm && \
    rm -f /root/*.rpm && \
    yum clean all

