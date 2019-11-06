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

    debsFetch = common.shellSequence(
        commands=[
            common.shellArg(
                command=[
                    'mkdir', '-p',
                    util.Interpolate(
                        'binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s')
                ],
                logfile="prep"),
            common.shellArg(
                command=util.Interpolate(
                    "scp {{ buildbot_scp_builds_fetch }}/* binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/"
                ),
                logfile="download")
        ],
        name="Fetching built artifacts from buildmaster")

    debsTarballVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate(
            'cat binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt'),
        # Note: We're overwriting this value to set it to the built revision rather than whatever it defaults to
        property="got_revision",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get build tarball revision")

    debsTarballShortVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate(
            'cat binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt | cut -c -9'),
        property="short_revision",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get build tarball short revision")

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

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                 util.Interpolate(
                     os.path.normpath("{{ deployed_debs }}")),
                 util.Interpolate(
                     os.path.normpath("{{ deployed_debs_symlink_base }}"))
                 ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    # Note: We're using a string here because using the array disables shell globbing!
    debsUpload = common.shellCommand(
        command=util.Interpolate(
            "scp -r outputs/%(prop:got_revision)s/* {{ buildbot_scp_debs }}"
        ),
        name="Upload debs to buildmaster")

    debsDeploy = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_debs_symlink }} && ln -s {{ deployed_debs }} {{ deployed_debs_symlink }}"
        ),
        flunkOnFailure=True,
        name="Deploy Debs")

    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(common.getPreflightChecks())
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(debsTarballVersion)
    f_package_debs.addStep(debsTarballShortVersion)
    f_package_debs.addStep(common.loadSigningKey())
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(masterPrep)
    f_package_debs.addStep(debsUpload)
    f_package_debs.addStep(debsDeploy)
    f_package_debs.addStep(common.getClean())
    f_package_debs.addStep(common.unloadSigningKey())

    return f_package_debs
