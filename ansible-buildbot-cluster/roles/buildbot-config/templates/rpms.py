# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

profiles = {
{% for branch in opencast %}
  '{{ branch }}': {{ opencast[branch]['profiles'] }},
{% endfor %}
}


@util.renderer
def getRPMBuilds(props):
    builds = []
    for profile in profiles[props.getProperty('branch_pretty')]:
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
        builds.append(util.ShellArg(
                command=[
                    'rpmsign',
                    '--addsign',
                    '--key-id', util.Interpolate("%(prop:signing_key)s"),
                    util.Interpolate("RPMS/noarch/opencast%(prop:pkg_major_version)s-" + profile + "-%(prop:pkg_major_version)s.x-%(prop:buildnumber)s.%(prop:short_revision)s.el7.noarch.rpm")
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile=profile + " signing"))
    return builds


def getBuildPipeline():

    rpmsClone = steps.Git(
                     repourl="{{ source_rpm_repo_url }}",
                     mode="full",
                     method="fresh",
                     flunkOnFailure=True,
                     haltOnFailure=True,
                     name="Cloning rpm packaging configs")

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
                    'sed',
                    '-i',
                    util.Interpolate('s/srcversion .../srcversion %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/g'),
                    util.Interpolate('opencast%(prop:pkg_major_version)s.spec')
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='version'),
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
                logfile='buildnumber'),
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
        commands=getRPMBuilds,
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
    f_package_rpms.addStep(rpmsClone)
    f_package_rpms.addStep(rpmsVersion)
    f_package_rpms.addStep(rpmsFetch)
    f_package_rpms.addStep(rpmsTarballVersion)
    f_package_rpms.addStep(rpmsTarballShortVersion)
    f_package_rpms.addStep(rpmsPrep)
    f_package_rpms.addStep(common.loadSigningKey())
    f_package_rpms.addStep(rpmsBuild)
    f_package_rpms.addStep(masterPrep)
    f_package_rpms.addStep(rpmsUpload)
    f_package_rpms.addStep(rpmsDeploy)
    f_package_rpms.addStep(common.getClean())
    f_package_rpms.addStep(common.unloadSigningKey())

    return f_package_rpms
