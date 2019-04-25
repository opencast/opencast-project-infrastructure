# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

profiles = ["admin", "adminpresentation", "adminworker", "allinone", "ingest", "migration", "presentation", "worker"]

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

def getRPMBuilds():
    builds = []
    for profile in profiles:
        builds.append(util.ShellArg(
                command=[
                    'rpmbuild',
                    '--define', 'ocdist ' + profile,
                    '--define', util.Interpolate('tarversion %(prop:pkg_major_version)s-SNAPSHOT'),
                    '-bb', '--noclean',
                    util.Interpolate("SPECS/opencast%(prop:pkg_major_version)s.spec")
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile=profile))
    return builds


def getBuildPipeline():

    rpmChecker = steps.SetPropertyFromCommand(
        command="[ -d .git ] && echo True || echo False",
        property="alreadyCloned",
        name="Checking if this is a fresh clone")

    rpmsClone = steps.ShellCommand(
        command=[
            'git', 'clone', "{{ source_rpm_repo_url }}", './'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasNotCloned,
        hideStepIf=hideIfAlreadyCloned,
        name="Cloning rpm packaging configs")

    rpmsUpdate = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['git', 'fetch'],
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='fetch'),
            util.ShellArg(
                command=[
                    'git', 'reset', '--hard',
                    util.Interpolate('origin/master')
                ],
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='checkout'),
            util.ShellArg(
                command=[
                    'git', 'clean', '-fdx'
                ],
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='clean')
        ],
        workdir="build",
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasCloned,
        hideStepIf=hideIfNotAlreadyCloned,
        name="Resetting rpm packaging configs")

    rpmsVersion = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="rpm_script_rev",
        flunkOnFailure=True,
        warnOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get rpm script revision")

    rpmsFetch = steps.ShellSequence(
        commands=[
            util.ShellArg(
			    #We're using a string here rather than an arg array since we need the shell functions
                command='echo -e "%_topdir `pwd`" > ~/.rpmmacros',
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="rpmdev-setup"),
            util.ShellArg(
                command=[
                    'rpmdev-setuptree'
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="rpmdev"),
            util.ShellArg(
                command=[
                    'mkdir', '-p',
                    'BUILD/opencast/build',
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="prep"),
            util.ShellArg(
                command=[
                    "scp",
                    util.Interpolate("{{ buildbot_scp_builds_fetch }}/*"),
                    "BUILD/opencast/build"
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="download"),
            util.ShellArg(
                command=[
                    "ln", "-sr",
                    util.Interpolate("opencast%(prop:pkg_major_version)s.spec"),
                    "SPECS"
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="specs"),
            util.ShellArg(
                #Same here
                command=util.Interpolate("ln -sr opencast%(prop:pkg_major_version)s/* SOURCES"),
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="sources")
        ],
        workdir="build/specs",
        name="Fetch built artifacts and build prep",
        haltOnFailure=True,
        flunkOnFailure=True)

    rpmsTarballVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate('cat BUILD/opencast/build/revision.txt'),
        property="got_revision", #Note: We're overwriting this value to set it to the built revision rather than whatever it defaults to
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build/specs",
        name="Get build tarball revision")

    rpmsTarballShortVersion = steps.SetPropertyFromCommand(
        command=util.Interpolate('cat BUILD/opencast/build/revision.txt | cut -c -9'),
        property="short_revision",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build/specs",
        name="Get build tarball short revision")

    rpmsPrep = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=[
                    'rpmdev-bumpspec',
                    '-u', '"Buildbot <buildbot@opencast.org>"',
                    '-c',
                    util.Interpolate(
                        'Opencast revision %(prop:got_revision)s, packaged with RPM scripts version %(prop:rpm_script_rev)s'
                    ),
                    util.Interpolate('opencast%(prop:pkg_major_version)s.spec')
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='rpmdev-bumpspec'),
            util.ShellArg(
                command=[
                    'sed',
                    '-i',
                    util.Interpolate('s/2%%{?dist}/%(prop:buildnumber)s.%(prop:short_revision)s%%{?dist}/g'),
                    util.Interpolate('opencast%(prop:pkg_major_version)s.spec')
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='sed'),
            util.ShellArg(
                command=['rm', '-f', 'BUILD/opencast/build/revision.txt'],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="cleanup")
        ],
        workdir="build/specs",
        name="Prepping rpms",
        haltOnFailure=True,
        flunkOnFailure=True)

    rpmsBuild = steps.ShellSequence(
        commands=getRPMBuilds(),
        workdir="build/specs",
        name="Build rpms",
        haltOnFailure=True,
        flunkOnFailure=True)

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_rpms }}")),
                util.Interpolate(os.path.normpath("{{ deployed_rpms_symlink_base }}"))
        ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    #Note: We're using a string here because using the array disables shell globbing!
    rpmsUpload = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r RPMS/noarch/* {{ buildbot_scp_rpms }}"
        ),
        workdir="build/specs",
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload rpms to buildmaster")

    rpmsDeploy = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_rpms_symlink }} && ln -s {{ deployed_rpms }} {{ deployed_rpms_symlink }}"
        ),
        flunkOnFailure=True,
        name="Deploy rpms")

    f_package_rpms = util.BuildFactory()
    f_package_rpms.addStep(common.getPreflightChecks())
    f_package_rpms.addStep(rpmChecker)
    f_package_rpms.addStep(rpmsClone)
    f_package_rpms.addStep(rpmsUpdate)
    f_package_rpms.addStep(rpmsVersion)
    f_package_rpms.addStep(rpmsFetch)
    f_package_rpms.addStep(rpmsTarballVersion)
    f_package_rpms.addStep(rpmsTarballShortVersion)
    f_package_rpms.addStep(rpmsPrep)
    f_package_rpms.addStep(rpmsBuild)
    f_package_rpms.addStep(masterPrep)
    f_package_rpms.addStep(common.getPermissionsFix())
    f_package_rpms.addStep(rpmsUpload)
    f_package_rpms.addStep(rpmsDeploy)
    f_package_rpms.addStep(common.getClean())
    f_package_rpms.addStep(steps.Trigger(schedulerNames=[util.Interpolate("%(prop:branch_pretty)s RPM Repo Triggerable")], name="Trigger package repo build"))

    return f_package_rpms
