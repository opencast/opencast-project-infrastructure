FROM centos:8
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#Not in stable yet
#COPY opencast.repo /etc/yum.repos.d/
COPY opencast-testing.repo /etc/yum.repos.d/

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y \
        bash \
     # Run deps
        tesseract \
        tesseract-langpack-deu \
        nmap-ncat \
# not built yet due to lack of time
#        synfig \
        ffmpeg \
# not built yet due to dependency issues
#        sox \
        hunspell \
        hunspell-en \
        java-1.8.0-openjdk && \
    yum clean all

