# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common


class GenerateDeleteCommands(buildstep.ShellMixin, steps.BuildStep):

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
                common.AWSStep(
                    command=['s3', 'rm', 's3://{{ s3_public_bucket }}/builds/' + target],
                    name="Removing " + target.split("/")[1])
                for target in self.extract_targets(self.observer.getStdout())
            ])
        return result



def __getBasePipeline():

    f_build = util.BuildFactory()

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()

    return f_build


def getBuildPipeline():

    getDate = steps.SetPropertyFromCommand(
        command="date +%Y-%m-%d -d '{{ keep_artifacts }} day ago'",
        property="cutoff_date",
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Determine cutoff date")


    cleanup = GenerateDeleteCommands(
        command=util.Interpolate("aws --endpoint-url {{ s3_host }} s3api list-objects-v2 --bucket {{ s3_public_bucket }} --prefix builds/ --query 'Contents[?LastModified<=`%(prop:cutoff_date)s`].Key' | jq '.[] | split(\"/\")[1:3] | join(\"/\")' | sort | uniq"),
        name="Determining cleanup targets",
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.public_access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.public_secret_key")
        })

    f_build = __getBasePipeline()
    f_build.addStep(getDate)
    f_build.addStep(cleanup)

    return f_build
