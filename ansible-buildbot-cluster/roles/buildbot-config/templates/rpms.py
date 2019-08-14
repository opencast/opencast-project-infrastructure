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
        builds.append(common.shellArg(
                command=[
                    'rpmbuild',
                    '--define', 'ocdist ' + profile,
                    '--define', util.Interpolate('tarversion %(prop:pkg_major_version)s-SNAPSHOT'),
                    '-bb', '--noclean',
                    util.Interpolate("SPECS/opencast%(prop:pkg_major_version)s.spec")
                ],
                logfile=profile))
        builds.append(common.shellArg(
                command=[
                    'rpmsign',
                    '--addsign',
                    '--key-id', util.Interpolate("%(prop:signing_key)s"),
                    util.Interpolate("RPMS/noarch/opencast%(prop:pkg_major_version)s-" + profile + "-%(prop:pkg_major_version)s.x-%(prop:buildnumber)s.%(prop:short_revision)s.el7.noarch.rpm")
                ],
                logfile=profile + " signing"))
    return builds


def getBuildPipeline():

    rpmsClone = steps.Git(
                     repourl="{{ source_rpm_repo_url }}",
                     branch="master",
                     alwaysUseLatest=True,
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

    rpmsFetch = common.shellSequence(
        commands=[
            common.shellArg(
			    #We're using a string here rather than an arg array since we need the shell functions
                command='echo -e "%_topdir `pwd`" > ~/.rpmmacros',
                logfile="rpmdev-setup"),
            common.shellArg(
                command=[
                    'rpmdev-setuptree'
                ],
                logfile="rpmdev"),
            common.shellArg(
                command=[
                    'mkdir', '-p',
                    'BUILD/opencast/build',
                ],
                logfile="prep"),
            common.shellArg(
                command=[
                    "scp",
                    util.Interpolate("{{ buildbot_scp_builds_fetch }}/*"),
                    "BUILD/opencast/build"
                ],
                logfile="download"),
            common.shellArg(
                command=[
                    "ln", "-sr",
                    util.Interpolate("opencast%(prop:pkg_major_version)s.spec"),
                    "SPECS"
                ],
                logfile="specs"),
            common.shellArg(
                #Same here
                command=util.Interpolate("ln -sr opencast%(prop:pkg_major_version)s/* SOURCES"),
                logfile="sources")
        ],
        workdir="build/specs",
        name="Fetch built artifacts and build prep")

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

    rpmsPrep = common.shellSequence(
        commands=[
            common.shellArg(
                command=[
                    'sed',
                    '-i',
                    util.Interpolate('s/srcversion .../srcversion %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/g'),
                    util.Interpolate('opencast%(prop:pkg_major_version)s.spec')
                ],
                logfile='version'),
            common.shellArg(
                command=[
                    'rpmdev-bumpspec',
                    '-u', '"Buildbot <buildbot@opencast.org>"',
                    '-c',
                    util.Interpolate(
                        'Opencast revision %(prop:got_revision)s, packaged with RPM scripts version %(prop:rpm_script_rev)s'
                    ),
                    util.Interpolate('opencast%(prop:pkg_major_version)s.spec')
                ],
                logfile='rpmdev-bumpspec'),
            common.shellArg(
                command=[
                    'sed',
                    '-i',
                    util.Interpolate('s/2%%{?dist}/%(prop:buildnumber)s.%(prop:short_revision)s%%{?dist}/g'),
                    util.Interpolate('opencast%(prop:pkg_major_version)s.spec')
                ],
                logfile='buildnumber'),
            common.shellArg(
                command=['rm', '-f', 'BUILD/opencast/build/revision.txt'],
                logfile="cleanup")
        ],
        workdir="build/specs",
        name="Prepping rpms")

    rpmsBuild = common.shellSequence(
        commands=getRPMBuilds,
        workdir="build/specs",
        name="Build rpms")

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_rpms }}")),
                util.Interpolate(os.path.normpath("{{ deployed_rpms_symlink_base }}"))
        ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    #Note: We're using a string here because using the array disables shell globbing!
    rpmsUpload = common.shellCommand(
        command=util.Interpolate(
            "scp -r RPMS/noarch/* {{ buildbot_scp_rpms }}"
        ),
        workdir="build/specs",
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
