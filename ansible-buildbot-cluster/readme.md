BuildBot
==========

These scripts setup BuildBot and configure it for Opencast usage.  Buildbot runs as its own user, so a second login user
is required.  Please see the infrastructure users playbook to set those up!  To deploy/update BuildBot, run:

    #TODO: ansible-playbook -k -K -i hosts user-setup.yml [--limit host-or-group]
