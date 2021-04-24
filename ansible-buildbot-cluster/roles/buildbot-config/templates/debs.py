# -*- python -*-
# ex: set filetype=python:

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
                logname='dch'),
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
                    'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:oc_commit)s/revision.txt'
                ),
                logname='revision')
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
    f_package_debs.addStep(removeSymlinks)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(common.loadSigningKey())
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(common.unloadSigningKey())
    f_package_debs.addStep(debsUpload)
    f_package_debs.addStep(common.getClean())

    return f_package_debs
