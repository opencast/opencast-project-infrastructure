# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers
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


class GeneratePerImageBuilds(buildstep.ShellMixin, steps.BuildStep):

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

    @util.renderer
    def getDatetime(self):
        return datetime.utcnow().strftime('%Y-%m-%d:T%H:%M:%SZ')

    @defer.inlineCallbacks
    def run(self):
        # run the command to get the list of targets
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        # if the command passes extract the list of stages
        result = cmd.results()
        if result == util.SUCCESS:
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([ docker(target) for target in self.extract_targets(self.observer.getStdout())
                for docker in (
                    lambda target:
                        steps.SetProperty(
                            property="fdnwj",
                            doStepIf=target == "base",
                            hideStepIf=target != "base",
                            value=util.Interpolate(f"ocqa-%(prop:docker_image)s-worker-base"),
                            name=util.Interpolate("Blanking fdnwj build variable")),
                    lambda target:
                        steps.SetProperty(
                            property="fdnwj",
                            doStepIf=target != "base",
                            hideStepIf=target == "base",
                            value=util.Interpolate(f"ocqa-%(prop:docker_image)s-worker-base-{ target }"),
                            name=f"Setting fdnwj variable to { target }"),
                    lambda target:
                        common.shellCommand(
                            command=["docker", "build", ".",
                                "--build-arg", util.Interpolate("VERSION=%(prop:buildbot_version)s"),
                                "--build-arg", util.Interpolate(f"BUILD_DATE={ self.getDatetime }"),
                                "--target", target,
                                "-t", util.Interpolate(f"%(prop:docker_host)s/%(prop:fdnwj)s:latest")],
                            workdir=util.Interpolate("build/docker-qa-images/%(prop:fdn)s"),
                            name=util.Interpolate(f"Building %(prop:docker_image)s { target } %(prop:docker_tag:-buildbot_version)s")),
                    lambda target:
                        common.shellCommand(
                            command=["docker", "tag",
                                util.Interpolate("%(prop:docker_host)s/%(prop:fdnwj)s:latest"),
                                util.Interpolate("%(prop:docker_host)s/%(prop:fdnwj)s:%(prop:docker_tag:-buildbot_version)s")],
                            name=util.Interpolate(f"Tagging %(prop:docker_imagej)s { target } latest as %(prop:docker_tag:-buildbot_version)s")),
                    lambda target:
                        common.shellCommand(
                            command=["docker", "tag",
                                util.Interpolate("%(prop:docker_host)s/%(prop:fdnwj)s:latest"),
                                util.Interpolate("greglogan/%(prop:fdnwj)s:latest")],
                            doStepIf="greglogan" != util.Property("docker_host"),
                            hideStepIf="greglogan" == util.Property("docker_host"),
                            name=util.Interpolate(f"Tagging %(prop:docker_image)s { target } latest for upstream as well")),
                    lambda target:
                        common.shellCommand(
                            command=["docker", "push", util.Interpolate("%(prop:docker_host)s/%(prop:fdnwj)s:latest")],
                            timeout=240,
                            name=util.Interpolate(f"Pushing %(prop:docker_image)s { target } latest")),
                    lambda target:
                        common.shellCommand(
                            command=["docker", "push", util.Interpolate("greglogan/%(prop:fdnwj)s:latest")],
                            timeout=240,
                            doStepIf="greglogan" != util.Property("docker_host"),
                            hideStepIf="greglogan" == util.Property("docker_host"),
                            name=util.Interpolate(f"Pushing greglogan %(prop:docker_image)s { target } latest")),
                    lambda target:
                        common.shellCommand(
                            command=["docker", "push", util.Interpolate("%(prop:docker_host)s/%(prop:fdnwj)s:%(prop:docker_tag)s")],
                            timeout=240,
                            name=util.Interpolate(f"Pushing %(prop:docker_image)s { target } %(prop:docker_tag)s"),
                            doStepIf=lambda step: "latest" != util.Property("docker_tag"),
                            hideStepIf=lambda results, step: "latest" != util.Property("docker_tag"))
                )
            ])
        return result


class Docker():

    REQUIRED_PARAMS = [
        "workernames"
        ]

    OPTIONAL_PARAMS = [
        ]

    props = {}

    def __init__(self, props):
        for key in Docker.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Docker.OPTIONAL_PARAMS:
            if key in props and type(props[key]) in [str, list]:
                self.props[key] = props[key]


    @util.renderer
    def selectDockerHostUserSecret(props):
        secretId = str(props.getProperty("docker_host")) + "-docker-user"
        return util.Secret(secretId)


    @util.renderer
    def selectDockerHostPassSecret(props):
        secretId = str(props.getProperty("docker_host")) + "-docker-pass"
        return util.Secret(secretId)


    cloneDockerfiles = common.getClone(url="{{ infra_repo_url }}", branch=util.Property("docker_branch", default=util.Property("branch")))

    setFullDockerImageName = steps.SetProperty(
            property="fdn",
            value=util.Interpolate("ocqa-%(prop:docker_image)s-worker-base"))

    dockerLogin = common.shellCommand(
            command=["docker", "login", "-u", selectDockerHostUserSecret, "-p", selectDockerHostPassSecret, util.Interpolate("%(prop:docker_host)s")],
            name=util.Interpolate("Logging into %(prop:docker_host)s"))

    dockerLoginUpstream = common.shellCommand(
            command=["docker", "login", "-u", util.Secret("greglogan-docker-user"), "-p", util.Secret("greglogan-docker-pass")],
            doStepIf="greglogan" != util.Property("docker_host"),
            hideStepIf="greglogan" == util.Property("docker_host"),
            name="Logging into Dockerhub")

    #FIXME: Unused?
    removeDockerTag = common.shellCommand(
            command=["docker", "rmi", "-f", util.Interpolate("ocqa-%(prop:docker_image)s-worker:%(prop:docker_tag)s")],
            name=util.Interpolate("Untagging ocqa-%(prop:docker_image)s-worker:%(prop:docker_tag)s"))

    pruneDockerImages = common.shellCommand(
            command=["docker", "system", "prune", "-f"],
            timeout=600,
            name="Pruning Docker")


    def getPushPipeline(self):

        generatePerImageBuilds = GeneratePerImageBuilds(
            command=util.Interpolate("grep FROM docker-qa-images/%(prop:fdn)s/Dockerfile | cut -f 4 -d ' '"),
            name="Determining image targets",
            haltOnFailure=True,
            flunkOnFailure=True)

        # This pipeline runs once per image type
        f_build = util.BuildFactory()
        f_build.addStep(self.cloneDockerfiles)
        f_build.addStep(self.setFullDockerImageName)
        f_build.addStep(self.dockerLogin)
        f_build.addStep(self.dockerLoginUpstream)
        f_build.addStep(generatePerImageBuilds)
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


    def getPullPipeline(self):

        pullDockerImage = common.shellCommand(
            command=['docker', 'pull', util.Interpolate("%(prop:docker_host)s/%(prop:fdn)s:%(prop:docker_tag)s")],
            name=util.Interpolate("Fetching %(prop:fdn)s:%(prop:docker_tag)s image"))

        # This pipline runs once per *worker* and handles all of the images
        f_get = util.BuildFactory()
        f_get.addStep(self.cloneDockerfiles)
        f_get.addStep(self.dockerLogin)
        f_get.addStep(self.setFullDockerImageName)
        f_get.addStep(pullDockerImage)
        f_get.addStep(self.pruneDockerImages)
        f_get.addStep(common.getClean())

        return f_get


    def getSpawnerPipeline(self):

        generateBuilds = GenerateDockerBuilds(
            command="ls docker-qa-images | grep worker-base | cut -f 2 -d '-'",
            name="Determining target images",
            haltOnFailure=True,
            flunkOnFailure=True)


        f_spawner = util.BuildFactory()
        f_spawner.addStep(self.cloneDockerfiles)
        f_spawner.addStep(generateBuilds)

        return f_spawner


    def getCleanerPipeline(self):

        f_cleaner = util.BuildFactory()
        f_cleaner.addStep(self.pruneDockerImages)

        return f_cleaner


    def getBuilders(self):

        builders = []

        #Spawn all of the individual container builds
        builders.append(util.BuilderConfig(
            name="ocqa worker build spawner",
            workernames=self.props['workernames'],
            factory=self.getSpawnerPipeline()))

        #Triggerable scheduler to catch the above trigger steps
        builders.append(util.BuilderConfig(
            name="ocqa worker build",
            collapseRequests=False,
            workernames=self.props['workernames'],
            factory=self.getPushPipeline()))

        #Each worker has its own builder since this has to execute on every single worker
        for worker in self.props["workernames"]:
            builders.append(util.BuilderConfig(
                name="ocqa worker " + worker + " finalizer",
                collapseRequests=False,
                workernames=self.props['workernames'],
                factory=self.getPullPipeline()))
            #NB: This gets fired by the maintenance scheduler!
            builders.append(util.BuilderConfig(
                name=f"ocqa { worker } docker cleanup",
                workernames=self.props['workernames'],
                factory=self.getCleanerPipeline()))

        return builders


    def getSchedulers(self):

        scheds = {}

        scheds['docker_spawner'] = schedulers.SingleBranchScheduler(
            name="ocqa spawner scheduler",
            builderNames=["ocqa worker build spawner"],
            fileIsImportant=lambda change: any(map(lambda filename: "docker-qa-images" in filename, change.files)),
            onlyImportant=True,
            change_filter=util.ChangeFilter(category="push", branch_re='f/buildbot'))

        scheds['docker_image'] = schedulers.Triggerable(
            name="ocqa image triggerable",
            builderNames=["ocqa worker build"])

        scheds['docker_finalizer'] = schedulers.Triggerable(
            name="ocqa finalizer triggerable",
            builderNames=["ocqa worker " + worker + " finalizer" for worker in self.props["workernames"]])

        scheds["docker_force"] = schedulers.ForceScheduler(
            name="ocqaforce",
            buttonName="Force Build",
            label="Force Build Settings",
            builderNames=["ocqa worker build spawner"],
            codebases=[
                  util.CodebaseParameter(
                      "",
                      label="Dockerfile source branch",
                      # will generate a combo box
                      branch=util.StringParameter(
                          name="branch",
                          default="f/buildbot"
                      ),
                      # will generate nothing in the form, but revision, repository,
                      # and project are needed by buildbot scheduling system so we
                      # need to pass a value ("")
                      revision=util.FixedParameter(name="revision", default="HEAD"),
                      repository=util.FixedParameter(
                          name="repository", default="{{ infra_repo_url }}"),
                      project=util.FixedParameter(name="project", default=""),
                  )],

            # in case you don't require authentication this will display
            # input for user to type his name
            username=util.UserNameParameter(label="your name:", size=80),

            properties=[
              util.StringParameter(name="buildbot_version", label="Buildbot Version", default="{{ docker_image_tag }}"),
              util.StringParameter(name="docker_tag", label="Docker Tag", default="latest")
            ])

        return scheds
