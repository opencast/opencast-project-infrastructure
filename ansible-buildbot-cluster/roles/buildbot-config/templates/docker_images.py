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
                        'buildbot_version': util.Property("buildbot_version", default="{{ docker_image_buildbot_version }}"),
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
        command="ls docker-qa-images | grep worker-base | cut -f 2 -d '-'",
        name="Determining target images",
        haltOnFailure=True,
        flunkOnFailure=True)

setFullDockerImageName = steps.SetProperty(
        property="fdn",
        value=util.Interpolate("ocqa-%(prop:docker_image)s-worker-base"))

@util.renderer
def getDatetime():
    return datetime.utcnow().strftime('%Y-%m-%d:T%H:%M:%SZ')

buildDockerImage = common.shellCommand(
        command=["docker", "build", ".",
            "--build-arg", util.Interpolate("VERSION=%(prop:buildbot_version)s"),
            "--build-arg", f"BUILD_DATE={ str(getDatetime) }",
            "-t", util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:latest")],
        workdir=util.Interpolate("build/docker-qa-images/%(prop:fdn)s"),
        name=util.Interpolate("Building %(prop:fdn)s:%(prop:docker_tag:-buildbot_version)s"))

tagImage = common.shellCommand(
        command=["docker", "tag",
            util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:latest"),
            util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:%(prop:docker_tag:-buildbot_version)s")],
        workdir=util.Interpolate("build/docker-qa-images/%(prop:fdn)s"),
        name=util.Interpolate("Tagging %(prop:fdn)s:latest as %(prop:docker_tag:-buildbot_version)s"))

dockerLogin = common.shellCommand(
        command=["docker", "login", "-u", selectDockerHostUserSecret, "-p", selectDockerHostPassSecret, util.Interpolate("%(prop:docker_host)s")],
        name=util.Interpolate("Logging into %(prop:docker_host)s"))

pushlatestDockerImage = common.shellCommand(
        command=["docker", "push", util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:latest")],
        name=util.Interpolate("Pushing %(prop:fdn)s:latest"))

pushDockerImage = common.shellCommand(
        command=["docker", "push", util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:%(prop:docker_tag)s")],
        name=util.Interpolate("Pushing %(prop:fdn)s:%(prop:docker_tag)s"),
        doStepIf=lambda step: "latest" != util.Property("docker_tag"),
        hideStepIf=lambda results, step: "latest" != util.Property("docker_tag"))

pullDockerImage = common.shellCommand(
        command=['docker', 'pull', util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:%(prop:docker_tag)s")],
        name=util.Interpolate("Fetching %(prop:fdn)s:%(prop:docker_tag)s image"))

removeDockerTag = common.shellCommand(
        command=["docker", "rmi", "-f", util.Interpolate("ocqa-%(prop:docker_image)s-worker:%(prop:docker_tag)s")],
        name=util.Interpolate("Untagging ocqa-%(prop:docker_image)s-worker:%(prop:docker_tag)s"))

pruneDockerImages = common.shellCommand(
        command=["docker", "system", "prune", "-f"],
        name="Pruning Docker")


def getPushPipeline():

    # This pipeline runs once per image type
    f_build = util.BuildFactory()
    f_build.addStep(cloneDockerfiles)
    f_build.addStep(setFullDockerImageName)
    f_build.addStep(buildDockerImage)
    f_build.addStep(tagImage)
    f_build.addStep(dockerLogin)
    f_build.addStep(pushlatestDockerImage)
    f_build.addStep(pushDockerImage)
    f_build.addStep(steps.Trigger(
        name=util.Interpolate("Triggering pull of %(prop:docker_image)s"),
            schedulerNames=["ocqa finalizer triggerable"],
            #We need to check for tags like 'v3.7.0', where we remove the v, and 'latest', where we don't.
            doStepIf=util.Property("docker_tag", default="latest") in ("{{ docker_image_tag[1:] }}", "{{ docker_image_tag }}"),
            waitForFinish=False,
            alwaysUseLatest=True,
            set_properties={
                'docker_image': util.Property("docker_image"), 
                'docker_tag': util.Property("docker_tag"),
                'docker_host': util.Property("docker_host"),
                'docker_branch': util.Property('docker_branch')
            }))
    f_build.addStep(common.getClean())

    return f_build

def getPullPipeline():

    # This pipline runs once per *worker* and handles all of the images
    f_get = util.BuildFactory()
    f_get.addStep(cloneDockerfiles)
    f_get.addStep(dockerLogin)
    f_get.addStep(setFullDockerImageName)
    f_get.addStep(pullDockerImage)
    f_get.addStep(pruneDockerImages)
    f_get.addStep(common.getClean())
    
    return f_get

def getSpawnerPipeline():

    f_spawner = util.BuildFactory()
    f_spawner.addStep(cloneDockerfiles)
    f_spawner.addStep(generateBuilds)

    return f_spawner
