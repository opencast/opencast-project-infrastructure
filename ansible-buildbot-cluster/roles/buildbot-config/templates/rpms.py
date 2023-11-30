# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers
import common
import json
import random

repo_lock = util.MasterLock("rpm_repo_lock", maxCount=1)

class Rpms():

    REQUIRED_PARAMS = [
        "git_branch_name",
        "pkg_major_version",
        "branch_pretty",
        "profiles",
        "el",
        "workernames"
        ]

    OPTIONAL_PARAMS = [
        "Build"
        ]

    props = {}
    pretty_branch_name = None
    build_sched = None
    profiles = []


    def __init__(self, props):
        for key in Rpms.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Rpms.OPTIONAL_PARAMS:
            if "Build" == key:
                self.build_sched = props[key]
            if key in props:
                self.props[key] = props[key]

        self.pretty_branch_name = self.props["branch_pretty"]

    @util.renderer
    def getRPMBuilds(props):
        builds = []
        for profile in self.profiles[props.getProperty('branch_pretty')]:
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


    def getBuildPipeline(self):

        rpmsClone = common.getClone(
            url="{{ source_rpm_repo_url }}",
            branch=util.Interpolate("%(prop:rpmspec_override:-%(prop:branch)s)s"))

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
            commands=self.getRPMBuilds,
            workdir="build/rpmbuild/SPECS",
            name="Build rpms")

        # Note: We're using a string here because using the array disables shell globbing!
        rpmsUpload = common.shellCommand(
            command=util.Interpolate("mkdir -p /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch && mv -v rpmbuild/RPMS/noarch/* /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch/"),
            name="Upload rpms to S3")

        rpmsPrune = common.shellCommand(
            command=util.Interpolate("ls -t /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch | grep allinone | tail -n +6 | cut -f 4 -d '-' | while read version; do rm -f /builder/s3/repo/rpms/unstable/el/%(prop:el_version)s/oc-%(prop:pkg_major_version)s/noarch/*$version; done"),
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


    def getBuilders(self):

        builders = []

        cent_props = dict(self.props)
        cent_props['image'] = random.choice({{ docker_centos_worker_images }})

        for distro in self.props['el']:
            el_props = dict(self.props)
            el_props['el_version'] = distro
            el_props['image'] = f"cent{distro}"
            lock = util.MasterLock(f"{ self.props['git_branch_name'] }rpm_el{ distro }_lock", maxCount=1)

            if "Develop" == self.pretty_branch_name:
                #Set the RPM branch to master
                el_props['rpmspec_override'] = "master"
                #Override/set a bunch of the build props since the RPM's dont relaly have a develop...

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + f" el{distro} RPM Packaging",
                factory=self.getBuildPipeline(),
                workernames=self.props['workernames'],
                properties=el_props,
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

        return builders


    def getSchedulers(self):

        raise RuntimeError("Check packages.py for the RPM schedulers")

        scheds = {}

        if None == self.build_sched:
            sched = schedulers.Nightly(
                name=self.pretty_branch_name + ' RPM Package Generation',
                change_filter=util.ChangeFilter(category=None, branch_re=self.props['git_branch_name']),
                hour={{ nightly_build_hour }},
                onlyIfChanged=True,
                properties=self.props,
                builderNames=[ f"{ self.pretty_branch_name } el{ el_mapping[version] } RPM Packaging" for version in el_mapping ])
        else:
            sched = schedulers.Dependent(
                name=self.pretty_branch_name + " RPM Packaging Generation",
                upstream=self.build_sched,
                properties=self.props,
                builderNames=[
                    self.pretty_branch_name + " el7 RPM Packaging",
                    self.pretty_branch_name + " el8 RPM Packaging",
                    self.pretty_branch_name + " el9 RPM Packaging"
                ])
        scheds[f"{ self.pretty_branch_name }Rpms"] = sched

        return scheds
