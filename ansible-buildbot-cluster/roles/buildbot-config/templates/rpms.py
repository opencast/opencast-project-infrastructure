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
        "workernames",
        "rpm_signing_key_id",
        "rpm_signing_key_file"
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
            if key in props and type(props[key]) in [str, list]:
                self.props[key] = props[key]

        self.pretty_branch_name = self.props["branch_pretty"]
        self.profiles = self.props['profiles']
        if 'pkg_minor_version' not in self.props:
            self.props["pkg_minor_version"] = "x"
        self.props["signing_key_filename"] = self.props["rpm_signing_key_file"]
        self.props["signing_key_id"] = self.props["rpm_signing_key_id"]

    def getRPMBuild(self, profile):
        return common.shellSequence(
            commands=[
                common.shellArg(
                    command=[
                        'mv',
                        util.Interpolate(f"SOURCES/opencast-dist-{ profile }-%(prop:pkg_major_version)s-SNAPSHOT.tar.gz"),
                        util.Interpolate(f"SOURCES/opencast-dist-{ profile }-%(prop:pkg_major_version)s.tar.gz")],
                    logname=profile + " rename tarball"),
                common.shellArg(
                    command=[
                        'rpmbuild',
                        '--define', 'ocdist ' + profile,
                        '-ba',
                        'SPECS/opencast.spec'],
                    logname=profile),
                common.shellArg(
                    command=[
                        'rpmsign',
                        '--addsign',
                        '--key-id', util.Interpolate("%(prop:signing_key)s"),
                        util.Interpolate(
                            "RPMS/noarch/opencast-" + profile + "-%(prop:pkg_major_version)s-%(prop:rpm_version)s.el%(prop:el_version)s.noarch.rpm")
                    ],
                    logname=profile + " signing")
            ],
            workdir="build/rpmbuild",
            name=f"Building { profile } RPM")

    def getBuildPipeline(self):

        rpmsClone = common.getClone(
            url="{{ source_rpm_repo_url }}",
            branch=util.Interpolate("%(prop:branch)s"))

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
            value=util.Interpolate("git%(prop:short_revision)s.%(prop:buildnumber)s"),
            name="Calculate desired RPM version")

        rpmsSetup = common.shellSequence(
            commands=[
                common.shellArg(
                    # We're using a string here rather than an arg array since we need the shell functions
                    command='echo -e "%_topdir `pwd`" > ~/.rpmmacros',
                    logname="rpmdev-setup-topdir"),
                common.shellArg(
                    command=util.Interpolate('echo "%%octarversion %(prop:pkg_major_version)s" >> ~/.rpmmacros'),
                    logname="rpmdev-setup-tarversion"),
                common.shellArg(
                    command=util.Interpolate('echo "%%ocversion %(prop:pkg_major_version)s" >> ~/.rpmmacros'),
                    logname="rpmdev-setup-tarversion"),
                common.shellArg(
                    command=util.Interpolate('echo "%%ocrelease %(prop:rpm_version)s" >> ~/.rpmmacros'),
                    logname="rpmdev-setup-tarversion"),
            ],
            workdir="build/rpmbuild",
            name="Prep rpm environment")

        rpmsCheck = common.checkAWS(
            path="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            name="Checking that build exists in S3")

        rpmsFetch = common.syncAWS(
            pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            pathTo="rpmbuild/SOURCES",
            name="Fetch build from S3")

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
            timeout=1800,
            name="Building repository")

        f_package_rpms = util.BuildFactory()
        f_package_rpms.addStep(common.getPreflightChecks())
        f_package_rpms.addStep(rpmsClone)
        f_package_rpms.addStep(rpmsVersion)
        f_package_rpms.addStep(common.getLatestBuildRevision())
        f_package_rpms.addStep(common.getShortBuildRevision())
        f_package_rpms.addStep(rpmsFullVersion)
        f_package_rpms.addStep(rpmsSetup)
        f_package_rpms.addStep(rpmsCheck)
        f_package_rpms.addStep(rpmsFetch)
        f_package_rpms.addStep(common.loadSigningKey())
        for profile in self.profiles:
            f_package_rpms.addStep(self.getRPMBuild(profile))
        f_package_rpms.addStep(common.unloadSigningKey())
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


            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + f" el{distro} RPM Packaging",
                factory=self.getBuildPipeline(),
                workernames=self.props['workernames'],
                properties=el_props,
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

        return builders


    def getSchedulers(self):

        #NOTE: The RPMs do not currently define testing and release pipelines since Lars is doing them
        # If we ever move that into buildbot, take a look at how the debs are doing it
        return {}

