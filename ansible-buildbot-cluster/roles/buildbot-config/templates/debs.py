# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def getBuildPipeline():

    debsClone = steps.Git(repourl="{{ source_deb_repo_url }}",
                      branch=util.Property('branch'),
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

    debsFetch = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=[
                    'mkdir', '-p',
                    util.Interpolate('binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s')
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="prep"),
            util.ShellArg(
                command=util.Interpolate(
                    "scp {{ buildbot_scp_builds_fetch }}/* binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/"
                ),
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="download")
        ],
        name="Fetching built artifacts from buildmaster",
        haltOnFailure=True,
        flunkOnFailure=True)

    debsTarballVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate('cat binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt'),
        property="got_revision", #Note: We're overwriting this value to set it to the built revision rather than whatever it defaults to
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get build tarball revision")

    debsTarballShortVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate('cat binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt | cut -c -9'),
        property="short_revision",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get build tarball short revision")

    debsBuild = steps.ShellSequence(
        commands=[
            util.ShellArg(
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
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile='dch'),
            util.ShellArg(
                command=[
                    'rm', '-f', util.Interpolate("binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/revision.txt")
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile='cleanup'),
            util.ShellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                ),
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='write'),
            util.ShellArg(
                command=util.Interpolate(
                    'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s.orig.tar.xz'
                ),
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='link'),
            util.ShellArg(
                command=['bash', 'build.sh'],
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='build'),
            util.ShellArg(
                command=util.Interpolate(
                    'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:oc_commit)s/revision.txt'
                ),
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='revision')
        ],
        env={
            "NAME": "Buildbot",
            "EMAIL": "buildbot@ci.opencast.org",
            "SIGNING_KEY": util.Interpolate("%(prop:signing_key)s")
        },
        workdir="build",
        name="Build debs",
        haltOnFailure=True,
        flunkOnFailure=True)

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_debs }}")),
                util.Interpolate(os.path.normpath("{{ deployed_debs_symlink_base }}"))
        ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    #Note: We're using a string here because using the array disables shell globbing!
    debsUpload = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r outputs/%(prop:got_revision)s/* {{ buildbot_scp_debs }}"
        ),
        haltOnFailure=True,
        flunkOnFailure=True,
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
