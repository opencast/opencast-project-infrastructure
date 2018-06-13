# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import os.path
import common


def __getBasePipeline():

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())

    return f_build

def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline(pretty_branch_name):

    #Note: We're using a string here because using the array disables shell globbing!
    uploadTarballs = steps.ShellCommand(
        command=util.Interpolate(
            "scp build/*.tar.gz {{ buildbot_scp_builds }}"),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload build to buildmaster")

    setPrettyName = steps.SetProperty(
        property="branch_pretty",
        value=pretty_branch_name,
        name="Set pretty branch name")

    f_build = __getBasePipeline()
    f_build.addStep(common.getMasterPrep())
    f_build.addStep(common.getPermissionsFix())
    f_build.addStep(uploadTarballs)
    f_build.addStep(common.getClean())

    return f_build
