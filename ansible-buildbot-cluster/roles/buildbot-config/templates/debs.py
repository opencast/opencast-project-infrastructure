# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common
import json


def getBuildPipeline():

    debsClone = steps.Git(repourl="{{ source_deb_repo_url }}",
                          branch=util.Property('branch'),
                          alwaysUseLatest=True,
                          mode="full",
                          method="fresh",
                          flunkOnFailure=True,
                          haltOnFailure=True,
                          name="Cloning deb packaging configs")

    debsVersion = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="deb_script_rev",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get Debian script revision")

    removeSymlinks = common.shellCommand(
        command=['rm', '-rf', 'binaries', 'outputs'],
        alwaysRun=True,
        name="Prep cloned repo for CI use")

    debsFetch = common.syncAWS(
        pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
        pathTo="binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/",
        name="Fetch build from S3")

    debsBuild = common.shellSequence(
        commands=[
            common.shellArg(
                command=[
                    './changelog',
                    util.Property("pkg_major_version"),
                    util.Property("pkg_minor_version"),
                    util.Interpolate("%(prop:buildnumber)s-%(prop:short_revision)s"),
                    "unstable"
                ],
                logname='changelog'),
            common.shellArg(
                command=[
                    'rm', '-f',
                    util.Interpolate("binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt")
                ],
                logname='cleanup'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                ),
                logname='write'),
            common.shellArg(
                command=util.Interpolate(
                    'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s.orig.tar.xz'
                ),
                logname='link'),
            common.shellArg(
                command=['bash', 'build.sh'],
                logname='build'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:deb_script_rev)s/revision.txt'
                ),
                logname='revision')
        ],
        env={
            "NAME": "Buildbot",
            "EMAIL": "buildbot@{{ groups['master'][0] }}",
            "SIGNING_KEY": util.Interpolate("%(prop:signing_key)s")
        },
        name="Build debs")

    debRepoClone = common.getClone(url="{{ source_deb_packaging_repo_url }}",
                          branch="{{ deb_packaging_repo_branch }}",
                          name="Cloning deb repo configs")

    debRepoLoadKeys = common.shellCommand(
        command=['./build-keys'],
        name="Loading repo sig verification keys")

    debRepoCreate = common.shellCommand(
        command=['./create-branch', util.Interpolate("%(prop:pkg_major_version)s.x")],
        name=util.Interpolate("Ensuring %(prop:pkg_major_version)s.x repos exist"))


    debRepoIngest = common.shellCommand(
        command=['./include-binaries', util.Interpolate("%(prop:pkg_major_version)s.x"), util.Interpolate("%(prop:repo_component)s"), util.Interpolate("outputs/%(prop:deb_script_rev)s/opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.x-%(prop:buildnumber)s-%(prop:short_revision)s_amd64.changes")],
        name=util.Interpolate(f"Adding build to %(prop:pkg_major_version)s.x-%(prop:repo_component)s"))

    debRepoPrune = common.shellCommand(
        command=util.Interpolate("./snapshot-cleanup %(prop:pkg_major_version)s.x oc && ./clean-unstable-repo %(prop:pkg_major_version)s.x"),
        name=util.Interpolate(f"Pruning %(prop:pkg_major_version)s.x unstable repository"),
        alwaysRun=True)

    debRepoPublish = common.shellCommand(
        command=["./publish-branch", util.Interpolate("%(prop:pkg_major_version)s.x"), util.Interpolate("%(prop:signing_key)s"), "s3"],
        name=util.Interpolate("Publishing %(prop:pkg_major_version)s.x"),
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.public_access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.public_secret_key")
        })

    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(common.getPreflightChecks())
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(common.getLatestBuildRevision())
    f_package_debs.addStep(common.getShortBuildRevision())
    f_package_debs.addStep(removeSymlinks)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(common.loadSigningKey())
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(debRepoClone)
    f_package_debs.addStep(debRepoLoadKeys)
    f_package_debs.addStep(common.deployS3fsSecrets())
    f_package_debs.addStep(common.mountS3fs())
    f_package_debs.addStep(debRepoCreate)
    f_package_debs.addStep(debRepoIngest)
    f_package_debs.addStep(debRepoPrune)
    f_package_debs.addStep(debRepoPublish)
    f_package_debs.addStep(common.unloadSigningKey())
    f_package_debs.addStep(common.unmountS3fs())
    f_package_debs.addStep(common.cleanupS3Secrets())
    f_package_debs.addStep(common.getClean())

    return f_package_debs
