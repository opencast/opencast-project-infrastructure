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
                    "../RPMS/noarch/opencast-" + profile + "-%(prop:rpm_version)s.el%(prop:el_version)s.noarch.rpm")
            ],
            logname=profile + " signing"))
    return builds


def getBuildPipeline():

    rpmsClone = steps.Git(
        repourl="{{ source_rpm_repo_url }}",
        branch=util.Interpolate("%(prop:rpmspec_override:-%(prop:branch)s)s"),
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

    rpmsFullVersion = steps.SetProperty(
        property="rpm_version",
        value=util.Interpolate("%(prop:pkg_major_version)s.git%(prop:short_revision)s-%(prop:buildnumber)s"))

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
                    util.Interpolate('s/define srcversion .*$/define srcversion %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/g'),
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
                    util.Interpolate("s/\(Version: *\) .*/\\1 %(prop:pkg_major_version)s.git%(prop:short_revision)s/"),
                    util.Interpolate('opencast.spec')
                ],
                logname='version'),
            common.shellArg(
                command=[
                    'sed',
                    '-i',
                    util.Interpolate('s/2%%{?dist}/%(prop:buildnumber)s%%{?dist}/g'),
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
    rpmsUpload = common.shellCommand(
        command=util.Interpolate("mkdir -p /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch && mv -v rpmbuild/RPMS/noarch/* /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch/"),
        name="Upload rpms to S3")

    rpmsPrune = common.shellCommand(
        command=util.Interpolate("ls -t /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/noarch | grep allinone | tail -n +6 | cut -f 4 -d '-' | while read version; do rm -f /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/noarch/*$version; done"),
        name=util.Interpolate("Pruning %(prop:pkg_major_version)s unstable repository"),
        alwaysRun=True)

    repoMetadata = common.shellCommand(
        command=['createrepo', '.'],
        workdir=util.Interpolate("/builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch"),
        name="Building repository")

    f_package_rpms = util.BuildFactory()
    f_package_rpms.addStep(common.getPreflightChecks())
    f_package_rpms.addStep(rpmsClone)
    f_package_rpms.addStep(rpmsVersion)
    f_package_rpms.addStep(common.getLatestBuildRevision())
    f_package_rpms.addStep(common.getShortBuildRevision())
    f_package_rpms.addStep(rpmsFullVersion)
    f_package_rpms.addStep(rpmsSetup)
    f_package_rpms.addStep(rpmsFetch)
    f_package_rpms.addStep(rpmsPrep)
    f_package_rpms.addStep(common.loadSigningKey())
    f_package_rpms.addStep(rpmsBuild)
    f_package_rpms.addStep(common.unloadSigningKey())
    f_package_rpms.addStep(common.deployS3fsSecrets())
    f_package_rpms.addStep(common.mountS3fs())
    f_package_rpms.addStep(rpmsUpload)
    f_package_rpms.addStep(rpmsPrune)
    f_package_rpms.addStep(repoMetadata)
    f_package_rpms.addStep(common.unmountS3fs())
    f_package_rpms.addStep(common.cleanupS3Secrets())
    f_package_rpms.addStep(common.getClean())

    return f_package_rpms
