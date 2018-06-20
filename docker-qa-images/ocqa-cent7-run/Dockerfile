FROM centos:7
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#COPY ffmpeg*.deb /root/

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y \
     # Run deps
        tesseract \
        tesseract-langpack-deu \
        nmap-ncat \
#       synfig \
        sox \
        hunspell \
        hunspell-en \
        java-1.8.0-openjdk && \
    yum clean all

