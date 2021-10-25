# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common
import json

class GenerateCreateCommands(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        stepList = []
        for comp in ("stable", "testing", "unstable"):
            stepList.append(
                steps.SetPropertyFromCommand(
                    command=['curl', '-s', util.Interpolate(f'http://{{ repo_host }}:{{ repo_port }}/api/repos/%(prop:pkg_major_version)s.x-{ comp }')],
                    property=f"{ comp }_exists",
                    flunkOnFailure=True,
                    haltOnFailure=True,
                    name=f"Checking if { comp } repo exists")
            ),
            stepList.append(aptly_command(
                data={
                    "Name": f"%(prop:pkg_major_version)s.x-{comp}",
                    "Comment": f"%(prop:pkg_major_version)s.x { comp } packages",
                    "DefaultDistribution": "%(prop:pkg_major_version)s.x",
                    "DefaultComponent": comp
                },
                #This looks stupid, and it is, but it also appears to be more or less the cleanest way of doing this
                doStepIf=util.Interpolate(f"%(prop:{ comp }_exists)s") == util.Interpolate('{"error":"local repo with name %(prop:pkg_major_version)s.x-' + f'{ comp }' + ' not found"}'),
                endpoint='repos',
                name=util.Interpolate(f"Creating %(prop:pkg_major_version)s.x-{ comp }")))

        # run the command to get the list of targets
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        self.build.addStepsAfterCurrentStep(stepList)
        return cmd.results()

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
            if target and "node_modules/" != target:
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
            targets = self.extract_targets(self.observer.getStdout())
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.shellCommand(
                    command=['curl', '-s', '-F', util.Interpolate(f'file=@outputs/%(prop:got_revision)s/{ target }'), util.Interpolate('http://{{ repo_host }}:{{ repo_port }}/api/files/%(prop:pkg_major_version)s.x-%(prop:repo_component)s')],
                    name=f"Uploading file { index + 1 }/{ len(targets) } to repo")
                for index, target in enumerate(targets)
            ])
        return result

class GeneratePublishCommands(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

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
                aptly_command(
                    endpoint="publish/:.",
                    data={
                        "SourceKind": "local",
                        "Sources": [
                            {"Name": "%(prop:pkg_major_version)s.x-stable"},
                            {"Name": "%(prop:pkg_major_version)s.x-testing"},
                            {"Name": "%(prop:pkg_major_version)s.x-unstable"},
                        ],
                        "Architectures": ["all","amd64"],
                        "Distribution": "%(prop:pkg_major_version)s.x"
                    },
                    name=util.Interpolate("Publishing %(prop:pkg_major_version)s.x"))

                if len(self.observer.getStdout()) == 0 else
                aptly_command(
                    method="PUT",
                    endpoint="publish/:./%(prop:pkg_major_version)s.x",
                    name=util.Interpolate("Republishing %(prop:pkg_major_version)s.x"))
            ])
        return result

def aptly_command(endpoint, method="POST", data={}, name="", doStepIf=True):
    if type(name) == str and len(name) == 0:
        name=f"Invoking HTTP { method } on { endpoint }"
    return steps.HTTPStep(
        method=method,
        url=util.Interpolate(f'http://{{ repo_host }}:{{ repo_port }}/api/{ endpoint }'),
        headers={'Content-Type': 'application/json'},
        data=util.Interpolate(json.dumps(data)),
        haltOnFailure=True,
        doStepIf=doStepIf,
        name=name)


def getBuildPipeline():

    debsClone = steps.Git(repourl="{{ source_deb_repo_url }}",
                          branch=util.Property('branch'),
                          alwaysUseLatest=True,
                          mode="full",
                          method="fresh",
                          flunkOnFailure=True,
                          haltOnFailure=True,
                          name="Cloning deb packaging configs")

    debsVersion = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="deb_script_rev",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get Debian script revision")

    removeSymlinks = common.shellCommand(
        command=['rm', '-rf', 'binaries', 'outputs'],
        alwaysRun=True,
        name="Prep cloned repo for CI use")

    debsFetch = common.syncAWS(
        pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
        pathTo="binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/",
        name="Fetch build from S3")

    debsBuild = common.shellSequence(
        commands=[
            common.shellArg(
                command=[
                    'dch',
                    '--changelog', 'opencast/debian/changelog',
                    '--newversion',
                    util.Interpolate(
                        '%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s-%(prop:short_revision)s'),
                    '-b', '-D', 'unstable', '-u', 'low', '--empty',
                    util.Interpolate(
                        'Opencast revision %(prop:got_revision)s, packaged with Debian scripts version %(prop:deb_script_rev)s'
                    )
                ],
                logname='dch'),
            common.shellArg(
                command=[
                    'rm', '-f',
                    util.Interpolate("binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt")
                ],
                logname='cleanup'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                ),
                logname='write'),
            common.shellArg(
                command=util.Interpolate(
                    'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s.orig.tar.xz'
                ),
                logname='link'),
            common.shellArg(
                command=['bash', 'build.sh'],
                logname='build'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:oc_commit)s/revision.txt'
                ),
                logname='revision')
        ],
        env={
            "NAME": "Buildbot",
            "EMAIL": "buildbot@{{ groups['master'][0] }}",
            "SIGNING_KEY": util.Interpolate("%(prop:signing_key)s")
        },
        name="Build debs")

    debRepoCreate = GenerateCreateCommands(
        command="true",
        name="Ensuring repos exist")

    debsUpload = common.copyAWS(
        pathFrom="outputs",
        pathTo="s3://{ s3_public_bucket }}/",
        name="Uploading packages to S3")

#    debsUpload = GenerateIngestCommands(
#        command=util.Interpolate("ls outputs/%(prop:got_revision)s"),
#        name="Finding files to upload to the repo")

    debRepoIngest = aptly_command(
        endpoint='repos/%(prop:pkg_major_version)s.x-%(prop:repo_component)s/file/%(prop:pkg_major_version)s.x-%(prop:repo_component)s',
        name="Ingesting packages")

    debRepoPublish = GeneratePublishCommands(
        command=util.Interpolate("curl -s http://{{ repo_host }}:{{ repo_port }}/api/publish | jq -r '.[] | select(.Distribution==\"%(prop:pkg_major_version)s.x\")'"),
        name=util.Interpolate("Determining current publication status for %(prop:pkg_major_version)s.x"),
        haltOnFailure=True,
        flunkOnFailure=True)
   
    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(common.getPreflightChecks())
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(common.getLatestBuildRevision())
    f_package_debs.addStep(common.getShortBuildRevision())
    f_package_debs.addStep(removeSymlinks)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(common.loadSigningKey())
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(common.unloadSigningKey())
    f_package_debs.addStep(debRepoCreate)
    f_package_debs.addStep(debsUpload)
    f_package_debs.addStep(debRepoIngest)
    f_package_debs.addStep(debRepoPublish)
    f_package_debs.addStep(common.getClean())

    return f_package_debs
