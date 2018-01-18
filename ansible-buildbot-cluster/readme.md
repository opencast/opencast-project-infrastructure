BuildBot
==========

These scripts setup BuildBot and configure it for Opencast usage.  Buildbot runs as its own user, so a second login user
is required.  Please see the infrastructure users playbook to set those up!  To deploy BuildBot, run:

    ansible-playbook -K -i hosts buildbot.yml

To update BuildBot run:

    ansible-playbook -K -i hosts reconfig.yml

Requires:
  - Ansible 2.4 or newer
