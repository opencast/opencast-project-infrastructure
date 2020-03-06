# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import steps, util
import common


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

    debsFetch = common.syncAWS(
        pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
        pathTo="binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/",
        name="Fetch build from S3")

    debsBuild = common.shellSequence(
        commands=[
            common.shellArg(
                command=[
                    'dch',
                    '--changelog', 'opencast/debian/changelog',
                    '--newversion',
                    util.Interpolate(
                        '%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s-%(prop:short_revision)s'),
                    '-b', '-D', 'unstable', '-u', 'low', '--empty',
                    util.Interpolate(
                        'Opencast revision %(prop:got_revision)s, packaged with Debian scripts version %(prop:deb_script_rev)s'
                    )
                ],
                logfile='dch'),
            common.shellArg(
                command=[
                    'rm', '-f',
                    util.Interpolate("binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt")
                ],
                logfile='cleanup'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                ),
                logfile='write'),
            common.shellArg(
                command=util.Interpolate(
                    'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s.orig.tar.xz'
                ),
                logfile='link'),
            common.shellArg(
                command=['bash', 'build.sh'],
                logfile='build'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:oc_commit)s/revision.txt'
                ),
                logfile='revision')
        ],
        env={
            "NAME": "Buildbot",
            "EMAIL": "buildbot@{{ groups['master'][0] }}",
            "SIGNING_KEY": util.Interpolate("%(prop:signing_key)s")
        },
        name="Build debs")

    debsUpload = common.syncAWS(
        pathFrom="outputs/%(prop:got_revision)s",
        pathTo="s3://{{ s3_public_bucket }}/builds/{{ debs_fragment }}",
        name="Upload debs to buildmaster")


    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(common.getPreflightChecks())
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(common.getLatestBuildRevision())
    f_package_debs.addStep(common.getShortBuildRevision())
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(common.loadSigningKey())
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(common.unloadSigningKey())
    f_package_debs.addStep(debsUpload)
    f_package_debs.addStep(common.getClean())

    return f_package_debs
