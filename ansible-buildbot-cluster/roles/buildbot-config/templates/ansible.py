# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *

profiles = {
{% for branch in opencast %}
{% if 'server' in opencast[branch] %}
  '{{ branch }}': {{ opencast[branch]['server'], }},
{% endif %}
{% endfor %}
}


def getBuildPipeline():

    clone = steps.Git(repourl="{{ ansible_scripts_url }}",
                      branch=util.Property('branch'),
                      mode="full",
                      method="fresh")

    version = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="ansible_script_rev",
        flunkOnFailure=True,
        warnOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get ansible script revision")

    deps = steps.ShellCommand(
        command=['ansible-galaxy', 'install', '-r', 'requirements.yml'],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Installing Ansible dependencies")

    deploy = steps.ShellCommand(
        command=['ansible-playbook', '-i', 'hosts', 'opencast.yml'],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Deploying Opencast")


    f_ansible = util.BuildFactory()
    f_ansible.addStep(clone)
    f_ansible.addStep(version)
    f_ansible.addStep(deps)
    f_ansible.addStep(deploy)

    return f_ansible
