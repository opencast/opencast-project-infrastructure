# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def wasCloned(step):
    if step.getProperty("alreadyCloned") == "True":
        return True
    else:
        return False


def wasNotCloned(step):
    return not wasCloned(step)


def hideIfAlreadyCloned(results, step):
    return wasCloned(step)


def hideIfNotAlreadyCloned(results, step):
    return wasNotCloned(step)


def getBuildPipeline():

    debChecker = steps.SetPropertyFromCommand(
        command="[ -d .git ] && echo True || echo False",
        property="alreadyCloned",
        name="Checking if this is a fresh clone")

    debsClone = steps.ShellCommand(
        command=[
            'git', 'clone', "{{ source_deb_repo_url }}", '--branch',
            util.Property('branch'), './'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasNotCloned,
        hideStepIf=hideIfAlreadyCloned,
        name="Cloning debian packaging configs")

    debsUpdate = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['git', 'fetch'], flunkOnFailure=True,
                logfile='fetch'),
            util.ShellArg(
                command=[
                    'git', 'reset', '--hard',
                    util.Interpolate('origin/%(prop:branch)s')
                ],  #We use reset here to get rid of other entries in the changelog
                flunkOnFailure=True,
                logfile='checkout')
        ],
        workdir="build",
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasCloned,
        hideStepIf=hideIfNotAlreadyCloned,
        name="Resetting debian packaging configs")

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
                    util.Interpolate('binaries/%(prop:debs_package_version)s')
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="prep"),
            util.ShellArg(
                command=util.Interpolate(
                    "scp {{ buildbot_scp_builds_fetch }}/* binaries/%(prop:debs_package_version)s/"
                ),
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="download")
        ],
        name="Fetching built artifacts from buildmaster",
        haltOnFailure=True,
        flunkOnFailure=True)

    debsTarballVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate('cat binaries/%(prop:debs_package_version)s/revision.txt'),
        property="got_revision", #Note: We're overwriting this value to set it to the built revision rather than whatever it defaults to
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get build tarball revision")

    debsBuild = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=[
                    'dch',
                    '--changelog', 'opencast/debian/changelog',
                    '--newversion',
                    util.Interpolate(
                        '%(prop:debs_package_version)s-%(prop:buildnumber)-%(prop:got_revision)s'),
                    '-b', '-D', 'unstable', '-u', 'low', '--empty',
                    util.Interpolate(
                        'Build revision %(prop:got_revision)s, built with %(prop:deb_script_rev)s scripts'
                    )
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile='dch'),
            util.ShellArg(
                command=[
                    'rm', '-f', util.Interpolate("binaries/%(prop:debs_package_version)s/revision.txt")
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile='cleanup'),
            util.ShellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:debs_package_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                ),
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='write'),
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
            "EMAIL": "buildbot@ci.opencast.org"
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
        haltOnFailure=False,
        flunkOnFailure=True,
        name="Deploy Debs")

    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(debChecker)
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsUpdate)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(debsTarballVersion)
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(masterPrep)
    f_package_debs.addStep(common.getPermissionsFix())
    f_package_debs.addStep(debsUpload)
    f_package_debs.addStep(debsDeploy)
    f_package_debs.addStep(common.getClean())

    return f_package_debs
