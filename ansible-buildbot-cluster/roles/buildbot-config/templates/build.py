# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
import common

getBuildSize = common.shellCommand(
    command=['du', '-ch'],
    name='Getting current build dir size')

uploadTarballs = common.syncAWS(
    pathFrom="build",
    pathTo="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
    name="Upload build to S3")

buildFoundAt = steps.SetProperty(
    property="build_found_at",
    value=util.Interpolate("s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}/"),
    name="Set S3 location for binary fetch")

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
    f_build.addStep(getBuildSize)
{% if push_prs | default(False) %}
    f_build.addStep(common.getTarballs())
    f_build.addStep(uploadTarballs)
{% endif %}
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline():

    stampVersion = common.shellCommand(
        command=util.Interpolate("echo '%(prop:got_revision)s' | tee revision.txt"),
        name="Stamping the build")

    updateBuild = common.copyAWS(
        pathFrom="revision.txt",
        pathTo="s3://{{ s3_public_bucket }}/builds/%(prop:branch_pretty)s/latest.txt",
        name="Update latest build marker in S3")

    updateCrowdin = common.shellCommand(
        command=util.Interpolate("echo api_key: '%(secret:crowdin.key)s' >> .crowdin.yaml; echo crowdin --config .crowdin.yaml upload sources -b %(prop:branch)s"),
        doStepIf={{ push_crowdin }},
        hideStepIf={{ not push_crowdin }},
        name="Update Crowdin translation keys")

    f_build = __getBasePipeline()
    f_build.addStep(common.getWorkerPrep())
{% if deploy_snapshots %}
    f_build.addStep(common.loadMavenSettings())
    f_build.addStep(common.getBuild(override=['deploy', '-T 1C', '-Pnone', '-s', 'settings.xml']))
{% else %}
    f_build.addStep(common.getBuild())
{% endif %}
    f_build.addStep(getBuildSize)
    f_build.addStep(common.unloadMavenSettings())
    f_build.addStep(common.getTarballs())
    f_build.addStep(getBuildSize)
    f_build.addStep(stampVersion)
    f_build.addStep(uploadTarballs)
    f_build.addStep(buildFoundAt)
    f_build.addStep(updateBuild)
    f_build.addStep(updateCrowdin)
    f_build.addStep(common.getClean())

    return f_build
