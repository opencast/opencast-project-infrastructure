# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
from datetime import datetime
import common

class GenerateDockerBuilds(buildstep.ShellMixin, steps.BuildStep):

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
                steps.Trigger(
                    name=f"Triggering build of { target }",
                    schedulerNames=["ocqa image triggerable"],
                    waitForFinish=False,
                    alwaysUseLatest=True,
                    set_properties={
                        'buildbot_version': util.Property("buildbot_version"),
                        'docker_image': target,
                        'docker_tag': util.Property("docker_tag", default="{{ docker_image_tag }}"),
                        'docker_host': '{{ docker_image_user }}',
                        'docker_branch': util.Property("branch") })
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


@util.renderer
def selectDockerHostUserSecret(props):
    secretId = str(props.getProperty("docker_host")) + "-docker-user"
    return util.Secret(secretId)

@util.renderer
def selectDockerHostPassSecret(props):
    secretId = str(props.getProperty("docker_host")) + "-docker-pass"
    return util.Secret(secretId)

cloneDockerfiles = common.getClone(url="{{ infra_repo_url }}", branch=util.Property("docker_branch"))

generateBuilds = GenerateDockerBuilds(
        command="ls docker-qa-images | grep ocqa",
        name="Determining target images",
        haltOnFailure=True,
        flunkOnFailure=True)

@util.renderer
def getDatetime():
    return datetime.utcnow().strftime('%Y-%m-%d:T%H:%M:%SZ')

buildDockerImage = common.shellCommand(
        command=["docker", "build", ".",
            "--build-arg", util.Interpolate("VERSION=%(prop:buildbot_version:-docker_tag)s"),
            "--build-arg", f"BUILD_DATE={ str(getDatetime) }",
            "-t", util.Interpolate("%(prop:docker_host)s/%(prop:docker_image)s:%(prop:docker_tag:-buildbot_version)s")],
        workdir=util.Interpolate("build/docker-qa-images/%(prop:docker_image)s"),
        name=util.Interpolate("Building %(prop:docker_image)s:%(prop:docker_tag:-buildbot_version)s"))

sanityCheck = common.shellCommand(
        command="false",
        flunkOnFailure=False,
        haltOnFailure=False,
        name="Running sanity checks")

dockerLogin = common.shellCommand(
        command=["docker", "login", "-u", selectDockerHostUserSecret, "-p", selectDockerHostPassSecret, util.Interpolate("%(prop:docker_host)s")],
        name=util.Interpolate("Logging into %(prop:docker_host)s"))

pushDockerImage = common.shellCommand(
        command=["docker", "push", util.Interpolate("%(prop:docker_host)s/%(prop:docker_image)s:%(prop:docker_tag)s")],
        name=util.Interpolate("Pushing %(prop:docker_image)s:%(prop:docker_tag)s"))

pullDockerImage = common.shellCommand(
        command=['docker', 'build', '--pull', '.', '-t', util.Interpolate('%(prop:docker_image)s-worker:%(prop:docker_tag)s')],
        workdir=util.Interpolate("{{ buildbot_config }}/workers/%(prop:docker_image)s"),
        name=util.Interpolate("Building local %(prop:docker_image)s:%(prop:docker_tag)s image"),
        haltOnFailure=False,
        flunkOnFailure=True)

pruneDockerImages = common.shellCommand(
        command=["docker", "system", "prune", "-f"],
        name="Pruning Docker")

def getPushPipeline():

    # This pipeline runs once per image type
    f_build = util.BuildFactory()
    f_build.addStep(cloneDockerfiles)
    f_build.addStep(buildDockerImage)
    f_build.addStep(sanityCheck)
    f_build.addStep(dockerLogin)
    f_build.addStep(pushDockerImage)
    f_build.addStep(steps.Trigger(
        name=util.Interpolate("Triggering pull of %(prop:docker_image)s"),
            schedulerNames=["ocqa finalizer triggerable"],
            waitForFinish=False,
            alwaysUseLatest=True,
            set_properties={
                'docker_image': util.Property("docker_image"), 
                'docker_tag': util.Property("docker_tag"),
                'docker_host': util.Property("docker_host"),
                'docker_branch': util.Property('docker_branch')  }))
    f_build.addStep(common.getClean())

    return f_build

def getPullPipeline():

    # This pipline runs once per *worker* and handles all of the images
    f_get = util.BuildFactory()
    f_get.addStep(cloneDockerfiles)
    f_get.addStep(dockerLogin)
    f_get.addStep(pullDockerImage)
    f_get.addStep(pruneDockerImages)
    f_get.addStep(common.getClean())
    
    return f_get

def getSpawnerPipeline():

    f_spawner = util.BuildFactory()
    f_spawner.addStep(cloneDockerfiles)
    f_spawner.addStep(generateBuilds)

    return f_spawner
