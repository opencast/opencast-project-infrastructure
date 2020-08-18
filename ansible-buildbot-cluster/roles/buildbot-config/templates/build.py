# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util
import common


def __getBasePipeline():

    f_build = util.BuildFactory()
    f_build.addStep(common.getPreflightChecks())
    f_build.addStep(common.getClone())
    f_build.addStep(common.setLocale())
    f_build.addStep(common.setTimezone())

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())
    f_build.addStep(common.getClean())

    return f_build


def getBuildPipeline():

    override = ['install', '-P', 'dist']
    buildTarballs = common.getBuild(override=override, workdir="build/assemblies", name="Building the tarballs")

    stampVersion = common.shellCommand(
        command=util.Interpolate("echo '%(prop:got_revision)s' | tee revision.txt"),
        name="Stamping the build")

    uploadTarballs = common.syncAWS(
        pathFrom="build",
        pathTo="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
        name="Upload build to S3")

    updateBuild = common.copyAWS(
        pathFrom="revision.txt",
        pathTo="s3://{{ s3_public_bucket }}/builds/%(prop:branch_pretty)s/latest.txt",
        name="Update latest build marker in S3")

    updateCrowdin = common.shellCommand(
        command=util.Interpolate(
            "if [ -f .upload-crowdin.sh ]; then CROWDIN_API_KEY='%(secret:crowdin.key)s' bash .upload-crowdin.sh; fi"),
        env={
            "TRAVIS_PULL_REQUEST": "false",  # This is always false since the PR doesn't use this method
            "TRAVIS_BRANCH": util.Interpolate("%(prop:branch)s")
        },
        doStepIf={{ push_crowdin }},
        hideStepIf={{ not push_crowdin }},
        name="Update Crowdin translation keys")

    f_build = __getBasePipeline()
    f_build.addStep(common.getWorkerPrep())
{% if deploy_snapshots %}
    f_build.addStep(common.loadMavenSettings())
    f_build.addStep(common.getBuild(override=['clean', 'deploy', '-P', 'none', '-s', 'settings.xml']))
{% else %}
    f_build.addStep(common.getBuild())
{% endif %}
    f_build.addStep(common.unloadMavenSettings())
    f_build.addStep(buildTarballs)
    f_build.addStep(stampVersion)
    f_build.addStep(uploadTarballs)
    f_build.addStep(updateBuild)
    f_build.addStep(updateCrowdin)
    f_build.addStep(common.getClean())

    return f_build
