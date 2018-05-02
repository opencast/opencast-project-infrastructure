# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import os.path
import common


def getPullRequestPipeline():

    prep_PR_master = steps.MasterShellCommand(
        command=[
            'mkdir', '-p',
            util.Interpolate(os.path.normpath("{{ deployed_PR_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

    f_build = util.BuildFactory()
    f_build.addStep(
        steps.SetPropertyFromCommand(
            command="date -u +%FT%H-%M-%S",
            property="build_timestamp",
            flunkOnFailure=True,
            warnOnFailure=True,
            haltOnFailure=True,
            name="Get build timestamp"))
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())
    f_build.addStep(common.getMasterPrep())
    f_build.addStep(prep_PR_master)
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline():

    #Note: We're using a string here because using the array disables shell globbing!
    uploadTarballs = steps.ShellCommand(
        command=util.Interpolate(
            "scp build/*.tar.gz {{ buildbot_scp_builds_put }}"),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload build to buildmaster")

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())
    f_build.addStep(common.getMasterPrep())
    f_build.addStep(uploadTarballs)
    f_build.addStep(common.getClean())

    return f_build
