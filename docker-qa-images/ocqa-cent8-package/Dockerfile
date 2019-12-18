FROM greglogan/ocqa-cent8-doc:v2.5.1
MAINTAINER Greg Logan <gregorydlogan@gmail.com>

RUN yum install -y \
     # Package building deps
        createrepo \
        rpmdevtools \
        rpmlint \
        yum-utils \
        rpm-sign && \
    yum clean all

