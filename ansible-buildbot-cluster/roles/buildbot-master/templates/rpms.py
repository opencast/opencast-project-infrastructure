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

    rpmChecker = steps.SetPropertyFromCommand(
        command="[ -d .git ] && echo True || echo False",
        property="alreadyCloned",
        name="Checking if this is a fresh clone")

    rpmsClone = steps.ShellCommand(
        command=[
            'git', 'clone', "{{ source_deb_repo_url }}", '--branch',
            util.Property('branch'), './'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasNotCloned,
        hideStepIf=hideIfAlreadyCloned,
        name="Cloning rpm packaging configs")

    rpmsUpdate = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['git', 'fetch'], flunkOnFailure=True,
                logfile='fetch'),
            util.ShellArg(
                command=[
                    'git', 'reset', '--hard',
                    util.Interpolate('origin/master')
                ],
                flunkOnFailure=True,
                logfile='checkout')
        ],
        workdir="build",
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasCloned,
        hideStepIf=hideIfNotAlreadyCloned,
        name="Resetting debian packaging configs")

    rpmsVersion = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="deb_script_rev",
        flunkOnFailure=True,
        warnOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get rpm script revision")

    rpmsClean = steps.ShellCommand(
        command=['rm', '-rf', 'binaries', 'outputs'],
        workdir="build",
        flunkOnFailure=False,
        warnOnFailure=True,
        name="Cleaning debian packaging directories")

    rpmsPrep = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=[
                    'dch', '--newversion',
                    util.Interpolate(
                        '%(prop:debs_package_version)s-%(prop:got_revision)s'),
                    '-b', '-D', 'unstable', '-u', 'low', '--empty',
                    util.Interpolate(
                        'Build revision %(prop:oc_commit)s, built with %(prop:deb_script_rev)s scripts'
                    )
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='dch'),
            util.ShellArg(
                command=[
                    'git', 'config', 'user.email', 'buildbot@opencast.org'
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='email'),
            util.ShellArg(
                command=['git', 'config', 'user.name', 'Buildbot'],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='authorname'),
            util.ShellArg(
                command=[
                    'git', 'commit', '-am', 'Automated commit prior to build'
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='commit')
        ],
        workdir="build/opencast",
        name="Prepping rpms",
        haltOnFailure=True,
        flunkOnFailure=True)

    rpmsFetch = steps.ShellSequence(
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
                    "scp {{ buildbot_scp_builds }}/*.tar.gz binaries/%(prop:debs_package_version)s/"
                ),
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="download")
        ],
        name="Fetching built artifacts from buildmaster",
        haltOnFailure=True,
        flunkOnFailure=True)

    rpmsBuild = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:debs_package_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                ),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='write'),
            util.ShellArg(
                command=['bash', 'build.sh'],
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='build'),
            util.ShellArg(
                command=util.Interpolate(
                    'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:oc_commit)s/revision.txt'
                ),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='revision')
        ],
        workdir="build",
        name="Build rpms",
        haltOnFailure=True,
        flunkOnFailure=True)

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_rpms }}")),
                util.Interpolate(os.path.normpath("{{ deployed_rpms_symlink_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

    #Note: We're using a string here because using the array disables shell globbing!
    rpmssUpload = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r outputs/%(prop:got_revision)s/* {{ buildbot_scp_rpms }}"
        ),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload rpms to buildmaster")

    rpmssDeploy = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_rpms_symlink }} && ln -s {{ deployed_rpms }} {{ deployed_rpms_symlink }}"
        ),
        name="Deploy rpms")

    f_package_rpms = util.BuildFactory()
    f_package_rpms.addStep(rpmChecker)
    f_package_rpms.addStep(rpmsClone)
    f_package_rpms.addStep(rpmsUpdate)
    f_package_rpms.addStep(rpmsVersion)
    f_package_rpms.addStep(rpmsPrep)
    f_package_rpms.addStep(rpmsFetch)
    f_package_rpms.addStep(rpmsBuild)
    f_package_rpms.addStep(masterPrep)
    f_package_rpms.addStep(rpmsUpload)
    f_package_rpms.addStep(rpmsDeploy)
    f_package_rpms.addStep(common.getClean())

    return f_package_rpms
