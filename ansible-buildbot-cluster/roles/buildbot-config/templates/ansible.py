# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common

params = [
    "deb_repo_suite=%(prop:deploy_suite)s",
    "oc_deb_repo_url=http://%(prop:package_repo_host)s/debian",
    "oc_deb_key_url=%(prop:key_url)s",
    "oc_deb_key_id=%(prop:key_id)s",
    "rpm_repo_suite=%(prop:deploy_suite)s",
    "oc_rpm_repo_base_url=http://%(prop:package_repo_host)s/rpms",
    "oc_rpm_key_url=%(prop:key_url)s",
    "oc_rpm_key_id=%(prop:key_id)s",
    "ansible_user={{ buildbot_user }}"
]


class GenerateInstallCommands(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    def extract_targets(self, stdout):
        targets = []
        for line in stdout.split('\n'):
            target = str(line.strip())
            if target:
                targets.append(target)
        return targets

    @defer.inlineCallbacks
    def run(self):
        # run the command to get the list of targets
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        # if the command passes extract the list of stages
        result = cmd.results()
        if result == util.SUCCESS:
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.shellCommand(
                    command=['ansible-playbook',
                             '-b',
                             util.Interpolate(
                                 '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                             '-i', util.Interpolate(
                                 "{{ buildbot_config }}/envs/" + target),
                             'uninstall.yml', 'opencast.yml', 'reset.yml',
                             '--extra-vars', util.Interpolate(" ".join(params))],
                    name="Deploy Opencast to " + target + " env",
                    haltOnFailure=False,
                    flunkOnFailure=True)
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


class GenerateDeployCommands(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    def extract_targets(self, stdout):
        targets = []
        for line in stdout.split('\n'):
            target = str(line.strip())
            if target:
                targets.append(target)
        return targets

    @defer.inlineCallbacks
    def run(self):
        # run the command to get the list of targets
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        # if the command passes extract the list of stages
        result = cmd.results()
        if result == util.SUCCESS:
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.shellCommand(
                    command=['ansible',
                             '-e', 'ansible_user={{ buildbot_user }}',
                             util.Interpolate(
                                 '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                             '-i', util.Interpolate(
                                 "{{ buildbot_config }}/envs/" + target),
                             'admin_node',
                             '-m', 'copy',
                             '-a', util.Interpolate(
                                 'src={{ buildbot_config }}/opencast-ingest.sh dest=opencast-ingest.sh')],
                    name="Copy ingest script to " + target + " env",
                    haltOnFailure=False,
                    flunkOnFailure=True)
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


class GenerateIngestCommands(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    def extract_targets(self, stdout):
        targets = []
        for line in stdout.split('\n'):
            target = str(line.strip())
            if target:
                targets.append(target)
        return targets

    @defer.inlineCallbacks
    def run(self):
        # run the command to get the list of targets
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        # if the command passes extract the list of stages
        result = cmd.results()
        if result == util.SUCCESS:
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.shellCommand(
                    command=["ansible",
                             util.Interpolate(
                                 '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                             "-i", util.Interpolate(
                                 "{{ buildbot_config }}/envs/" + target),
                             "admin_node",
                             "-m", "shell", "-a", "bash opencast-ingest.sh",
                             "--extra-vars", util.Interpolate(" ".join(params))],
                    name="Ingest media to " + target + " env",
                    haltOnFailure=False,
                    flunkOnFailure=True)
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


def getBuildPipeline():

    clone = common.getClone(url="{{ ansible_scripts_url }}",
                      branch=util.Property('branch'))

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

    secrets = common.copyAWS(
        pathFrom="s3://{{ s3_private_bucket }}/{{ groups['master'][0] }}/env/%(prop:deploy_env)s",
        pathTo="%(prop:builddir)s/%(prop:deploy_env)s",
        name="Fetching deploy key")

    permissions = common.shellCommand(
        command=['chmod', '600', util.Interpolate("%(prop:builddir)s/%(prop:deploy_env)s")],
        name="Fixing deploy key permissions")

    install = GenerateInstallCommands(
        command=util.Interpolate("ls {{ buildbot_config }}/envs/ | grep %(prop:deploy_env)s"),
        name="Determining install targets",
        haltOnFailure=True,
        flunkOnFailure=True)

    deploy = GenerateDeployCommands(
        command=util.Interpolate("ls {{ buildbot_config }}/envs/ | grep %(prop:deploy_env)s"),
        name="Determining deploy targets",
        haltOnFailure=True,
        flunkOnFailure=True)

    sleep = common.shellCommand(
        command=["sleep", "300"],
        name="Sleeping to let Opencast finish starting up")

    # We aren't using -u here because this is executing in the same directory as the checked out ansible scripts, which
    # contains a group_vars/all.yml files specifying ansible_user
    ingest = GenerateIngestCommands(
        command=util.Interpolate("ls {{ buildbot_config }}/envs/ | grep %(prop:deploy_env)s"),
        name="Determining ingest targets",
        haltOnFailure=True,
        flunkOnFailure=True)

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
    f_ansible.addStep(permissions)
    f_ansible.addStep(install)
    f_ansible.addStep(deploy)
    f_ansible.addStep(sleep)
    f_ansible.addStep(ingest)
    f_ansible.addStep(cleanup)

    return f_ansible
