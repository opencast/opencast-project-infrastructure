# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import common


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

    deps = common.shellCommand(
        command=['ansible-galaxy', 'install', '-r', 'requirements.yml'],
        name="Installing Ansible dependencies")

    secrets = common.shellCommand(
        command=['scp',
                 util.Interpolate("{{ buildbot_scp_deploy_key }}"),
                 util.Interpolate("%(prop:builddir)s/%(prop:deploy_env)s")],
        name="Fetching deploy key")

    params = [
        "deb_repo_suite=%(prop:deploy_suite)s",
        "oc_deb_repo_url=http://%(prop:package_repo_host)s/debian",
        "oc_deb_key_url=%(prop:key_url)s",
        "oc_deb_key_id=%(prop:key_id)s",
        "rpm_repo_suite=%(prop:deploy_suite)s",
        "oc_rpm_repo_url=http://%(prop:package_repo_host)s/rpms",
        "oc_rpm_key_url=%(prop:key_url)s",
        "oc_rpm_key_id=%(prop:key_id)s",
        "repo_username=%(secret:repo.username)s",
        "repo_password=%(secret:repo.password)s",
        "ansible_user={{ buildbot_user }}"
    ]

    deploy = common.shellCommand(
        command=['ansible-playbook',
                 '-b',
                 util.Interpolate(
                     '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                 '-i', util.Interpolate(
                     "{{ buildbot_config }}/envs/%(prop:deploy_env)s"),
                 'uninstall.yml', 'opencast.yml', 'reset.yml',
                 '--extra-vars', util.Interpolate(" ".join(params))],
        name="Deploying Opencast")

    copy = common.shellCommand(
        command=['scp',
                 '-i', util.Interpolate(
                     '%(prop:builddir)s/%(prop:deploy_env)s'),
                 '{{ buildbot_config }}/opencast-ingest.sh',
                 util.Interpolate(
                     "{{ buildbot_scp_deploy_script }}")],
        name="Copying Ingest script to target server")

    sleep = common.shellCommand(
        command=["sleep", "300"],
        name="Sleeping to let Opencast finish starting up")

    # We aren't using -u here because this is executing in the same directory as the checked out ansible scripts, which
    # contains a group_vars/all.yml files specifying ansible_user
    run = common.shellCommand(
        command=["ansible",
                 "allinone",
                 util.Interpolate(
                     '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                 "-i", util.Interpolate(
                     "{{ buildbot_config }}/envs/%(prop:deploy_env)s"),
                 "-m", "shell", "-a", "bash opencast-ingest.sh",
                 "--extra-vars", util.Interpolate(" ".join(params))],
        name="Ingesting demo media")

    cleanup = common.shellCommand(
        command=['rm', '-rf',
                 util.Interpolate("%(prop:builddir)s/%(prop:deploy_env)s")],
        alwaysRun=True,
        name="Cleanup")

    f_ansible = util.BuildFactory()
    f_ansible.addStep(clone)
    f_ansible.addStep(version)
    f_ansible.addStep(deps)
    f_ansible.addStep(secrets)
    f_ansible.addStep(deploy)
    f_ansible.addStep(copy)
    f_ansible.addStep(sleep)
    f_ansible.addStep(run)
    f_ansible.addStep(cleanup)

    return f_ansible
