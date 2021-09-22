FROM debian:10
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

#We need Aptly 1.4+, which is in buster-backports and newer
#TODO Update this image to a debian 11 base
COPY debian-buster-backports.list /etc/apt/sources.list.d/

RUN apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https gnupg curl ca-certificates && \
    apt-get install -y -t buster-backports aptly gnupg1

COPY entrypoint.sh /opt

WORKDIR /mnt/aptly

CMD ["bash", "/opt/entrypoint.sh"] #["aptly", "-config=/mnt/aptly/aptly.conf", "api", "serve"]

