User Setup
==========

These scripts deal with the initial set-up of user accounts for servers part of
Opencast's project infrastructure. To deploy/update the settings run:

    ansible-playbook -k -K -i hosts server-user-setup.yml [--limit host-or-group]
