# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
import common

profiles = {
{% for branch in opencast %}
    '{{ branch }}': {{ opencast[branch]['profiles'] }},
{% endfor %}
}


@util.renderer
def getRPMBuilds(props):
    builds = []
    elvers = props.getProperty("image")[-1]
    for profile in profiles[props.getProperty('branch_pretty')]:
        builds.append(common.shellArg(
            command=[
                'rpmbuild',
                '--define', 'ocdist ' + profile,
                '--define', util.Interpolate('tarversion %(prop:pkg_major_version)s-SNAPSHOT'),
                '-bb', '--noclean',
                'opencast.spec'
            ],
            logname=profile))
        builds.append(common.shellArg(
            command=[
                'rpmsign',
                '--addsign',
                '--key-id', util.Interpolate("%(prop:signing_key)s"),
                util.Interpolate(
                    "../RPMS/noarch/opencast-" + profile + "-%(prop:pkg_major_version)s.x-%(prop:buildnumber)s.%(prop:short_revision)s.el" + elvers + ".noarch.rpm")
            ],
            logname=profile + " signing"))
    return builds


def getBuildPipeline():

    rpmsClone = steps.Git(
        repourl="{{ source_rpm_repo_url }}",
        branch=util.Property('branch'),
        alwaysUseLatest=True,
        shallow=True,
        mode="full",
        method="clobber",
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

    rpmsSetup = common.shellSequence(
        commands=[
            common.shellArg(
                # We're using a string here rather than an arg array since we need the shell functions
                command='echo -e "%_topdir `pwd`" > ~/.rpmmacros',
                logname="rpmdev-setup"),
        ],
        workdir="build/rpmbuild",
        name="Fetch built artifacts and build prep")

    rpmsFetch = common.syncAWS(
        pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
        pathTo="rpmbuild/SOURCES",
        name="Fetch build from S3")

    rpmsPrep = common.shellSequence(
        commands=[
            common.shellArg(
                command=[
                    'sed',
                    '-i',
                    util.Interpolate('s/srcversion ..../srcversion %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/g'),
                    util.Interpolate('opencast.spec')
                ],
                logname='version'),
            common.shellArg(
                command=[
                    'rpmdev-bumpspec',
                    '-u', '"Buildbot <buildbot@opencast.org>"',
                    '-c',
                    util.Interpolate(
                        'Opencast revision %(prop:got_revision)s, packaged with RPM scripts version %(prop:rpm_script_rev)s'
                    ),
                    util.Interpolate('opencast.spec')
                ],
                logname='rpmdev-bumpspec'),
            common.shellArg(
                command=[
                    'sed',
                    '-i',
                    util.Interpolate('s/2%%{?dist}/%(prop:buildnumber)s.%(prop:short_revision)s%%{?dist}/g'),
                    util.Interpolate('opencast.spec')
                ],
                logname='buildnumber'),
            common.shellArg(
                command=['rm', '-f', 'BUILD/opencast/build/revision.txt'],
                logname="cleanup")
        ],
        workdir="build/rpmbuild/SPECS",
        name="Prepping rpms")

    rpmsBuild = common.shellSequence(
        commands=getRPMBuilds,
        workdir="build/rpmbuild/SPECS",
        name="Build rpms")

    # Note: We're using a string here because using the array disables shell globbing!
    rpmsUpload = common.syncAWS(
        pathFrom="rpmbuild/RPMS/noarch",
        pathTo="s3://{{ s3_public_bucket }}/builds/{{ rpms_fragment }}",
        name="Upload rpms to buildmaster")

    f_package_rpms = util.BuildFactory()
    f_package_rpms.addStep(common.getPreflightChecks())
    f_package_rpms.addStep(rpmsClone)
    f_package_rpms.addStep(rpmsVersion)
    f_package_rpms.addStep(common.getLatestBuildRevision())
    f_package_rpms.addStep(common.getShortBuildRevision())
    f_package_rpms.addStep(rpmsSetup)
    f_package_rpms.addStep(rpmsFetch)
    f_package_rpms.addStep(rpmsPrep)
    f_package_rpms.addStep(common.loadSigningKey())
    f_package_rpms.addStep(rpmsBuild)
    f_package_rpms.addStep(common.unloadSigningKey())
    f_package_rpms.addStep(rpmsUpload)
    f_package_rpms.addStep(common.getClean())

    return f_package_rpms
