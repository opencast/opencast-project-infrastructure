BuildBot
==========

These scripts setup BuildBot and configure it for Opencast usage.  Buildbot runs as its own user, so a second login user
is required.  Please see the infrastructure users playbook to set those up!  To deploy BuildBot, run:

    ansible-playbook -K -i hosts buildbot.yml

To update BuildBot run:

    ansible-playbook -K -i hosts reconfig.yml

Requires:
  - Ansible 2.4 or newer
  - All hosts must have sudo pre-installed prior to playbook execution

GitHub Setup
============

Application Setup
-----------------

Create an OAUTH application on the org hosting the repository.  For Opencast this is
https://github.com/organizations/opencast/settings/applications.  For build.opencast.org the homepage URL is
`http(s)://build.opencast.org`, and the auth callback URL is `http(s)://build.opencast.org/auth/login`


Webhook Setup
-------------

Create a webhook in the repository.  For Opencast this is https://github.com/opencast/opencast/settings/hooks.  Create
a username, password, and secret locally.  The payload URL looks like this
`http://$USERNAME:$PASSWORD@build.opencast.org/change_hook/github`, and set the appropriate value in the secret value.
Set the webhook to push only Pushes and Pull Requests.  Other events are ignored.


Github User Setup
-----------------

To push build statuses to Github we are using Personal Access Tokens (User settings > Developer Settings > Personal
access tokens).  This token needs the `repo:status` permission only, and the status pushes appear as the user generating
the token.  Thus, we are using the `oc-bot` user account.

Buildbot Setup
==============

Core node
---------

Create a file in host\_vars named after your core node.  For Opencast this would be `build.opencast.org.yml`.
This file is overriding the general defaults defined in the `group_vars/all.yml`.  In it set the following keys:

* `github_client_id`
* `github_client_secret`
* `github_hook_user`
* `github_hook_pass`
* `github_hook_secret`
* `github_token`

Along with any other keys you wish to override.

Worker nodes
------------

Create a file for each worker node in host\vars named after the worker node.  For example, `builder01.opencast.org.yml`.
This file sets up what the worker node's identity is within Buildbot, and what it should build.  An example file is in
`host_vars/worker.yml`.
