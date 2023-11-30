# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common


class GenerateMarkdownCommands(buildstep.ShellMixin, steps.BuildStep):

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
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.shellCommand(
                    command=['mkdocs', 'build'],
                    name="Build " + target[:-1] + " docs",
                    workdir="build/docs/guides/" + target,
                    env={
                        "LC_ALL": "en_US.utf8",
                        "LANG": "en_US.utf8",
                        "OC_CTYPE": "en_US.utf8",
                        "PATH": "/builder/.local/bin:${PATH}"
                    },
                    haltOnFailure=False,
                    flunkOnFailure=True)
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result

class GenerateCompressionCommands(buildstep.ShellMixin, steps.BuildStep):

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
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.compressDir(
                    dirToCompress="docs/guides/" + target,
                    outputFile=target.split("/")[0] + ".tar.bz2")
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


class GenerateS3Commands(buildstep.ShellMixin, steps.BuildStep):

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
            # create a ShellCommand for each stage and add them to the build
            self.build.addStepsAfterCurrentStep([
                common.copyAWS(
                    pathFrom=target.split("/")[0] + ".tar.bz2",
                    pathTo="s3://{{ s3_public_bucket }}/builds/{{ markdown_fragment }}/" + target.split("/")[0] + ".tar.bz2",
                    name="Upload " + target.split("/")[0] + " to S3")
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result


class Markdown():

    REQUIRED_PARAMS = [
        "git_branch_name",
        "pkg_major_version",
        "branch_pretty",
        "workernames"
        ]

    OPTIONAL_PARAMS = [
        ]

    props = {}
    pretty_branch_name = None

    def __init__(self, props):
        for key in Markdown.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Markdown.OPTIONAL_PARAMS:
            if key in props:
                self.props[key]

        self.pretty_branch_name = self.props["branch_pretty"]
        self.buildFilter = lambda change: any(map(lambda filename: "docs/guides" in filename, change.files))

    def __getBasePipeline(self):

        npm_install = common.shellSequence(
            commands=[
                common.shellArg(
                    command=['npm', 'install'],
                    logname='npm_install'),
            ],
            workdir="build/docs/guides",
            name="Running npm install",
            haltOnFailure=True)

        npmCheck = common.shellSequence(
            commands=[
                common.shellArg(
                    command=['npm', 'test'],
                    haltOnFailure=False,
                    logname='markdown-cli'),
            ],
            workdir="build/docs/guides",
            name="Check Markdown doc formatting with markdown-cli",
            haltOnFailure=False)

        pip_install = common.shellSequence(
            commands=[
                common.shellArg(
                    command=['python3', '-m', 'pip', 'install', '-r', 'requirements.txt'],
                    haltOnFailure=False,
                    logname='markdown-cli'),
            ],
            workdir="build/docs/guides",
            name="Running pip install",
            haltOnFailure=True)

        build = common.shellCommand(
            command=['./.style-and-markdown-build.sh'],
            name="Running tests and building docs",
            env={
                "LC_ALL": "en_US.UTF-8",
                "LANG": "en_US.UTF-8",
                "OC_CTYPE": "en_US.UTF-8",
                "PATH": "/builder/.local/bin:${PATH}"
            },
            haltOnFailure=False,
            flunkOnFailure=True)

        markdown = GenerateMarkdownCommands(
            command='ls -d */',
            name="Determining available docs",
            workdir="build/docs/guides",
            haltOnFailure=True,
            flunkOnFailure=True)

        f_build = util.BuildFactory()
        f_build.addStep(common.getClone())
        f_build.addStep(npm_install)
        f_build.addStep(npmCheck)
        f_build.addStep(pip_install)
        f_build.addStep(build)
        f_build.addStep(markdown)

        return f_build


    def getPullRequestPipeline(self):

        f_build = self.__getBasePipeline()
        f_build.addStep(common.getClean())

        return f_build


    def getBuildPipeline(self):

        compress = GenerateCompressionCommands(
            command='ls -d */site',
            name="Determining available docs for compression",
            workdir="build/docs/guides",
            haltOnFailure=True,
            flunkOnFailure=True)

        upload = GenerateS3Commands(
            command='ls -d */site',
            name="Determining available docs for upload",
            workdir="build/docs/guides",
            haltOnFailure=True,
            flunkOnFailure=True)

        updateMarkdown = steps.MasterShellCommand(
            command=util.Interpolate(
                "rm -f {{ deployed_markdown_symlink }} && ln -s {{ deployed_markdown }} {{ deployed_markdown_symlink }}"
            ),
            flunkOnFailure=True,
            name="Deploy Markdown")

        f_build = self.__getBasePipeline()
        f_build.addStep(compress)
        f_build.addStep(upload)
        #f_build.addStep(updateMarkdown)
        f_build.addStep(common.getClean())

        return f_build


    def getBuilders(self):

        builders = []

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Pull Request Markdown",
            factory=self.getPullRequestPipeline(),
            workernames=self.props['workernames'],
            collapseRequests=True,
            properties=self.props))

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Markdown",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames'],
            properties=self.props))

        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }Markdown"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Markdown",
            change_filter=util.ChangeFilter(category=None, branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Markdown" ])

        #PR builds
        scheds[f"{ self.pretty_branch_name }MarkdownPR"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Pull Request Markdown",
            change_filter=util.ChangeFilter(category="pull", branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Pull Request Markdown" ])

        scheds[f"{ self.pretty_branch_name}MarkdownForce"] = common.getForceScheduler(
            props=self.props,
            build_type="Markdown",
            builderNames=[ self.pretty_branch_name + " Markdown" ])

        return scheds
