# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *

def getBuildPipeline():

    clone = steps.Git(repourl="{{ ansible_scripts_url }}",
                      branch=util.Property('branch'),
                      alwaysUseLatest=True,
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

    secrets = steps.ShellCommand(
        command=['scp', util.Interpolate("{{ buildbot_scp_deploy_key }}"), util.Interpolate("/tmp/%(prop:deploy_env)s")],
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Fetching deploy key")

    deploy = steps.ShellCommand(
        command=['ansible-playbook', '-i', util.Interpolate("{{ buildbot_config }}/envs/%(prop:deploy_env)s"), 'opencast.yml', util.Interpolate('--extra-vars="deb_repo_suite=%(prop:deploy_suite)s rpm_repo_suite=%(prop:deploy_suite)s repo_host=%(prop:package_repo_host)s oc_rpm_key_url=%(prop:key_url)s oc_deb_key_url=%(prop:key_url)s username=%(secret:repo.username)s password=%(secret:repo.password)s"')],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Deploying Opencast")

    cleanup = steps.ShellCommand(
        command=['rm', '-rf', util.Interpolate("/tmp/%(prop:deploy_env)s")],
        flunkOnFailure=True,
        alwaysRun=True,
        name="Cleanup")

    f_ansible = util.BuildFactory()
    f_ansible.addStep(clone)
    f_ansible.addStep(version)
    f_ansible.addStep(deps)
    f_ansible.addStep(secrets)
    f_ansible.addStep(deploy)
    f_ansible.addStep(cleanup)

    return f_ansible
