FROM centos:7
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

COPY ffmpeg*.deb /root/

RUN yum update -y && \
    yum install epel-release && \
    yum install \
     # Run deps
        tesseract \
        tesseract-langpack-deu \
        nmap-ncat \
 f       synfig \
        sox \
        hunspell \
        hunspell-en \
        openjdk-8-jre && \
    yum clean all

