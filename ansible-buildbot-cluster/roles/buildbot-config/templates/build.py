# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import os.path
import common


def __getBasePipeline():

    f_build = util.BuildFactory()
    f_build.addStep(common.getPreflightChecks())
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build


def getBuildPipeline():

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                 util.Interpolate(
                     os.path.normpath("{{ deployed_builds }}")),
                 util.Interpolate(
                     os.path.normpath("{{ deployed_builds_symlink_base }}"))

                 ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    # Note: We're using a string here because using the array disables shell globbing!
    uploadTarballs = common.shellCommand(
        command=util.Interpolate(
            "echo '%(prop:got_revision)s' | tee build/revision.txt && scp build/* {{ buildbot_scp_builds }}"),
        name="Upload build to buildmaster")

    updateBuild = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_builds_symlink }} && ln -s {{ deployed_builds }} {{ deployed_builds_symlink }}"
        ),
        flunkOnFailure=True,
        name="Deploy Build")

    updateCrowdin = common.shellCommand(
        command=util.Interpolate(
            "if [ -f .upload-crowdin.sh ]; then CROWDIN_API_KEY='%(secret:crowdin.key)s' bash .upload-crowdin.sh; fi"),
        env={
            "TRAVIS_PULL_REQUEST": "false", #This is always false since the PR doesn't use this method
            "TRAVIS_BRANCH": util.Interpolate("%(prop:branch)s")
        },
        doStepIf={{ push_crowdin }},
        hideStepIf={{ not push_crowdin }},
        name="Update Crowdin translation keys")

    f_build = __getBasePipeline()
    f_build.addStep(masterPrep)
    f_build.addStep(uploadTarballs)
    f_build.addStep(updateBuild)
    f_build.addStep(updateCrowdin)
    f_build.addStep(common.getClean())

    return f_build
