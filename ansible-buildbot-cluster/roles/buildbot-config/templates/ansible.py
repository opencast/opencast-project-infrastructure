# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common

params = [
    "deb_repo_suite=%(prop:repo_component)s",
    "oc_deb_repo_url=http://%(prop:package_repo_host)s/debian",
    "oc_deb_key_url=%(prop:key_base_url)s/%(prop:deb_signing_key_filename)s",
    "oc_deb_key_id=%(prop:deb_signing_key_id)s",
    "rpm_repo_suite=%(prop:repo_component)s",
    "oc_rpm_repo_base_url=http://%(prop:package_repo_host)s/rpms",
    "oc_rpm_key_url=%(prop:key_base_url)s/%(prop:rpm_signing_key_filename)s",
    "oc_rpm_key_id=%(prop:rpm_signing_key_id)s",
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
            self.build.addStepsAfterCurrentStep([ ansible(target) for target in self.extract_targets(self.observer.getStdout())
                for ansible in (
                    lambda target:
                        common.shellCommand(
                            command=['ansible',
                                     '-e', 'ansible_user={{ buildbot_user }}',
                                     util.Interpolate(
                                         '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                                     '-i', util.Interpolate(
                                         "{{ buildbot_config }}/envs/" + target),
                                     '-b',
                                     'admin_node',
                                     '-m', 'package',
                                     '-a', 'name=python3-pip state=present',
                                     '--extra-vars', util.Interpolate(" ".join(params))],
                            name=f"Ensure pip is installed in { target }",
                            haltOnFailure=False,
                            flunkOnFailure=True),
                    lambda target:
                        common.shellCommand(
                            command=['ansible',
                                     '-e', 'ansible_user={{ buildbot_user }}',
                                     util.Interpolate(
                                         '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                                     '-i', util.Interpolate(
                                         "{{ buildbot_config }}/envs/" + target),
                                     '-b',
                                     'admin_node',
                                     '-m', 'shell',
                                     '-a', 'pip3 install pyyaml pyjson requests',
                                     '--extra-vars', util.Interpolate(" ".join(params))],
                            name=f"Ensure ingest script requirements present in env",
                            haltOnFailure=False,
                            flunkOnFailure=True),
                    lambda target:
                        common.shellCommand(
                            command=['ansible',
                                     '-e', 'ansible_user={{ buildbot_user }}',
                                     util.Interpolate(
                                         '--private-key=%(prop:builddir)s/%(prop:deploy_env)s'),
                                     '-i', util.Interpolate(
                                         "{{ buildbot_config }}/envs/" + target),
                                     'admin_node',
                                     '-m', 'shell',
                                     '-a', 'wget https://raw.githubusercontent.com/lkiesow/opencast-ingest/main/ingest.py -O ingest.py;  wget https://raw.githubusercontent.com/lkiesow/opencast-ingest/main/media.yml -O media.yml',
                                     '--extra-vars', util.Interpolate(" ".join(params))],
                            name=f"Copy ingest script to { target } env",
                            haltOnFailure=False,
                            flunkOnFailure=True)
                        )
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
                             "-m", "shell", "-a", "python3 ingest.py",
                             '--extra-vars', util.Interpolate(" ".join(params))],
                    name="Ingest media to " + target + " env",
                    haltOnFailure=False,
                    flunkOnFailure=True)
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


class Ansible():

    REQUIRED_PARAMS = [
        "git_branch_name",
        "pkg_major_version",
        "ffmpeg",
        "cores",
        "branch_pretty",
        "workernames",
        "deploy_env",
        "deb_signing_key_filename",
        "deb_signing_key_id",
        "rpm_signing_key_filename",
        "rpm_signing_key_id",
        "repo_component",
        "UnstablePackages"
        ]

    OPTIONAL_PARAMS = [
        "key_base_url"
        ]


    props = {}
    pretty_branch_name = None
    packages_sched = None

    def __init__(self, props):
        self.props["key_base_url"] = "{{ key_base_url }}"
        for key in Ansible.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if "UnstablePackages" == key:
                self.package_sched = props[key]
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Ansible.OPTIONAL_PARAMS:
            if key in props and type(props[key]) in [str, list]:
                self.props[key] = props[key]

        self.pretty_branch_name = self.props["branch_pretty"]


    def getBuildPipeline(self):

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


    def getBuilders(self):

        builders = []

        deploy_props = dict(self.props)
        deploy_props['package_repo_host'] = "{{ repo_host }}"

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Ansible Deploy",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames'],
            properties=deploy_props,
            collapseRequests=True))

        return builders


    def getSchedulers(self):

        scheds = {}

        scheds[f"{ self.pretty_branch_name }Ansible"] = schedulers.Dependent(
            name=self.pretty_branch_name + " Ansible Deploy",
            upstream=self.package_sched,
            properties=self.props,
            builderNames=[self.pretty_branch_name + " Ansible Deploy"])

        scheds[f"{ self.pretty_branch_name }AnsibleForce"] = common.getForceScheduler(
            name=self.pretty_branch_name + "Ansible",
            props=self.props,
            builderNames=[self.pretty_branch_name + " Ansible Deploy"])

        return scheds
