# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
import common
import json
import random

repo_lock = util.MasterLock("deb_repo_lock", maxCount=1)

class Debs():

    REQUIRED_PARAMS = [
        "git_branch_name",
        "pkg_major_version",
        "branch_pretty",
        "workernames",
        "deb_signing_key_id",
        "deb_signing_key_file"
        ]

    OPTIONAL_PARAMS = [
        "Build"
        ]

    props = {}
    pretty_branch_name = None
    build_sched = None
    branch_key_filename = None

    def __init__(self, props):
        for key in Debs.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Debs.OPTIONAL_PARAMS:
            if "Build" == key:
                self.build_sched = props[key]
            if key in props and type(props[key]) in [str, list]:
                self.props[key] = props[key]

        self.pretty_branch_name = self.props["branch_pretty"]
        if 'pkg_minor_version' not in self.props:
            self.props["pkg_minor_version"] = "x"
        #The default, automated key
        self.props["signing_key_filename"] = "{{ signing_key_filename }}"
        self.props["signing_key_id"] = "{{ signing_key_id }}"
        self.branch_key_filename = self.props["deb_signing_key_file"]
        self.branch_key_id = self.props["deb_signing_key_id"]

    def addDebBuild(self, f_package_debs):

        debsClone = steps.Git(repourl="{{ source_deb_repo_url }}",
                              branch=util.Property('branch'),
                              alwaysUseLatest=True,
                              mode="full",
                              method="fresh",
                              flunkOnFailure=True,
                              haltOnFailure=True,
                              name="Cloning deb packaging configs")

        debsSetMinor = steps.SetPropertyFromCommand(
            command=util.Interpolate("echo %(prop:branch)s | cut -f 2 -d '.' | cut -f 1 -d '-'"),
            property="pkg_minor_version",
            flunkOnFailure=True,
            haltOnFailure=True,
            name="Set minor version property")

        debsVersion = steps.SetPropertyFromCommand(
            command="git rev-parse HEAD",
            property="deb_script_rev",
            flunkOnFailure=True,
            haltOnFailure=True,
            workdir="build",
            name="Get Debian script revision")

        debsTagVersion = steps.SetProperty(
          property="tag_version",
          value=util.Interpolate("%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s-%(prop:short_revision)s"),
          doStepIf=util.Property("release_build", default="false") != "true",
          hideStepIf=util.Property("release_build", default="false") == "true",
          name="Calculate expected build version")

        removeSymlinks = common.shellCommand(
            command=['rm', '-rf', 'outputs'],
            name="Prep cloned repo for CI use")

        debsCheckS3 = common.checkAWS(
            path="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            name="Checking that build exists in S3",
            doStepIf=util.Property("release_build", default="false") != "true",
            hideStepIf=util.Property("release_build", default="false") == "true")

        debsFetchFromS3 = common.syncAWS(
            pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            pathTo="binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/",
            name="Fetch build from S3",
            doStepIf=util.Property("release_build", default="false") != "true",
            hideStepIf=util.Property("release_build", default="false") == "true")

        debsFetchFromGitHub = common.shellCommand(
            command=["./fetch.sh", util.Interpolate("%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s")],
            workdir="build/binaries",
            name="Fetch release build from GitHub",
            doStepIf=util.Property("release_build", default="false") == "true",
            hideStepIf=util.Property("release_build", default="false") != "true")

        debsPrepBuild = common.shellSequence(
            commands=[
                common.shellArg(
                    command=[
                        './changelog',
                        util.Property("pkg_major_version"),
                        util.Property("pkg_minor_version"),
                        util.Interpolate("%(prop:buildnumber)s-%(prop:short_revision)s"),
                        "unstable"
                    ],
                    logname='changelog'),
                common.shellArg(
                    command=util.Interpolate(
                        'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s.orig.tar.xz'
                    ),
                    logname='link'),
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\nSIGNING_KEY=%(prop:signing_key_id)s doOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                    ),
                    logname='write'),
            ],
            env={
                "NAME": "Buildbot",
                "EMAIL": "buildbot@{{ groups['master'][0] }}",
            },
            name="Prep to build debs",
            doStepIf=util.Property("release_build", default="false") != "true",
            hideStepIf=util.Property("release_build", default="false") == "true")

        debsPrepReleaseBuild = common.shellSequence(
            commands=[
                common.shellArg(
                    command=util.Interpolate(
                        'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:branch)s.orig.tar.xz && ls'
                    ),
                    logname='link'),
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\nSIGNING_KEY=%(prop:deb_signing_key_id)s doOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:branch)s" | tee build.sh'
                    ),
                    logname='write'),
            ],
            name="Prep to build release debs",
            doStepIf=util.Property("release_build", default="false") == "true",
            hideStepIf=util.Property("release_build", default="false") != "true")

        debsBuild = common.shellSequence(
            commands=[
                common.shellArg(
                    command=['bash', 'build.sh'],
                    logname='build'),
                common.shellArg(
                    command=util.Interpolate(
                        'echo "Opencast version %(prop:got_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:deb_script_rev)s/revision.txt'
                    ),
                    logname='revision')
            ],
            env={
                "NAME": "Buildbot",
                "EMAIL": "buildbot@{{ groups['master'][0] }}",
                "SIGNING_KEY": util.Interpolate("%(prop:deb_signing_key_id)s")
            },
            name="Build debs")

        f_package_debs.addStep(common.getPreflightChecks())
        f_package_debs.addStep(debsClone)
        f_package_debs.addStep(debsSetMinor)
        f_package_debs.addStep(debsVersion)
        f_package_debs.addStep(common.getLatestBuildRevision(
            doStepIf=util.Property("release_build", default="false") != "true",
            hideStepIf=util.Property("release_build", default="false") == "true"))
        f_package_debs.addStep(common.getShortBuildRevision())
        f_package_debs.addStep(debsTagVersion)
        f_package_debs.addStep(removeSymlinks)
        f_package_debs.addStep(debsCheckS3)
        f_package_debs.addStep(debsFetchFromS3)
        f_package_debs.addStep(debsFetchFromGitHub)
        #NB: This can be either the default, or the per-branch depending on the *buidler* below
        f_package_debs.addStep(common.loadSigningKey())
        f_package_debs.addStep(debsPrepBuild)
        f_package_debs.addStep(debsPrepReleaseBuild)
        f_package_debs.addStep(debsBuild)
        #We unload here since we *might* be using a different key in a minute to sign the actual repo
        f_package_debs.addStep(common.unloadSigningKey())


    def setupRepo(self, f_package_debs):

        debRepoClone = common.getClone(url="{{ source_deb_packaging_repo_url }}",
                              branch="{{ deb_packaging_repo_branch }}",
                              name="Cloning deb repo configs")

        debRepoLoadKeys = common.shellCommand(
            command=['./build-keys'],
            name="Loading repo sig verification keys")

        f_package_debs.addStep(debRepoClone)
        f_package_debs.addStep(debRepoLoadKeys)


    def mountS3(self, f_package_debs, host="rados", access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        f_package_debs.addStep(common.shellCommand(
            command=[f'./mount.{ host }'],
            env={
                'AWSACCESSKEYID': util.Secret(access_key_secret_id),
                'AWSSECRETACCESSKEY': util.Secret(secret_key_secret_id)
            },
            name=f"Mounting { host } S3"))


    def includeRepo(self, f_package_debs, s3_target="s3:s3:"):

        debRepoCreate = common.shellCommand(
            command=['./create-branch', util.Interpolate("%(prop:pkg_major_version)s.x")],
            name=util.Interpolate("Ensuring %(prop:pkg_major_version)s.x repos exist"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

        debRepoIngest = common.shellCommand(
                command=['./include-binaries', util.Interpolate("%(prop:pkg_major_version)s.x"), util.Interpolate("%(prop:repo_component:-unstable)s"), util.Interpolate("outputs/%(prop:deb_script_rev)s/*.changes")],
            name=util.Interpolate(f"Adding build to %(prop:repo_component:-unstable)s"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

        debSnapshotCleanup = common.shellCommand(
            command=["./snapshot-cleanup", util.Interpolate("%(prop:pkg_major_version)s.x"), s3_target],
            name=util.Interpolate(f"%(prop:pkg_major_version)s.x repository snapshot cleanup"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

        debRepoPrune = common.shellCommand(
            command=["./clean-unstable-repo", util.Interpolate("%(prop:pkg_major_version)s.x")],
            name=util.Interpolate(f"Pruning %(prop:pkg_major_version)s.x unstable repository"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

        f_package_debs.addStep(debRepoCreate)
        f_package_debs.addStep(debRepoIngest)
        f_package_debs.addStep(debSnapshotCleanup)
        f_package_debs.addStep(debRepoPrune)


    def publishRepo(self, f_package_debs, repo="Testing", s3_target="s3:s3:", access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        debRepoPublish = common.shellCommand(
                command=["./publish-branch", util.Interpolate("%(prop:pkg_major_version)s.x"), s3_target, util.Interpolate("%(prop:deb_signing_key_id)s")],
            name=util.Interpolate("Publishing %(prop:pkg_major_version)s.x on " + s3_target),
            env={
                "AWS_ACCESS_KEY_ID": util.Secret(access_key_secret_id),
                "AWS_SECRET_ACCESS_KEY": util.Secret(secret_key_secret_id)
            },
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60) #Yes, 4 hours.  Publishing from LITE to RADOS can take a *long* time.

        debsNotifyMatrix = common.notifyMatrix(
            message="Opencast %(prop:tag_version)s is now in the Deb " + repo + " repo",
            roomId="{{ default_matrix_room }}",
            warnOnFailure=True,
            flunkOnFailure=False,
            doStepIf=util.Property("release_build", default="false") == "true" and s3_target == "s3:s3:",
            hideStepIf="s3:s3:" != s3_target)

        f_package_debs.addStep(common.loadSigningKey(self.branch_key_filename))
        f_package_debs.addStep(debRepoPublish)
        f_package_debs.addStep(debsNotifyMatrix)
        f_package_debs.addStep(common.unmountS3fs("/builder/s3/repo/debs"))


    def cleanup(self, f_package_debs):

        f_package_debs.addStep(common.unloadSigningKey())
        f_package_debs.addStep(common.cleanupS3Secrets())
        f_package_debs.addStep(common.getClean())


    def getBuildPipeline(self):

        f_package_debs = util.BuildFactory()
        self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="rados")
        self.includeRepo(f_package_debs, s3_target="s3:s3:")
        self.publishRepo(f_package_debs, s3_target="s3:s3:")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getTestPipeline(self):

        f_package_debs = util.BuildFactory()
        self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="rados", access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.includeRepo(f_package_debs, s3_target="s3:s3")
        #Note the s3 target here is the official default.  We override and re-set it here so it's clear wtf we're doing
        self.publishRepo(f_package_debs, s3_target="s3:s3:", access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getReleasePipeline(self):

        debRepoPromote = common.shellCommand(
                command=["./promote-package", "opencast", util.Property("tag_version"), util.Property("branch"), "testing", "stable"],
                name=util.Interpolate("Promoting %(prop:tag_version)s to stable"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        #NB: We are not building debs here, just promoting from test!
        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="rados", access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        f_package_debs.addStep(debRepoPromote)
        #Note the s3 target here is the official default.  We override and re-set it here so it's clear wtf we're doing
        self.publishRepo(f_package_debs, repo="Stable", s3_target="s3:s3:", access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getBuilders(self):

        builders = []

        deb_props = dict(self.props)
        deb_props['image'] = random.choice({{ docker_debian_worker_images }})
        deb_props['release_build'] = 'false'
        lock = util.MasterLock(f"{ self.props['git_branch_name'] }deb_lock", maxCount=1)

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Debian Packaging",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames'],
            properties=deb_props,
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        prod_props = dict(deb_props)
        prod_props['signing_key_filename'] = self.branch_key_filename
        prod_props['release_build'] = 'true'

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Testing Debian Packaging",
            factory=self.getTestPipeline(),
            workernames=self.props['workernames'],
            properties=dict(prod_props) | {"repo_component": "testing", "tag_version": util.Property('branch')},
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        if "Develop" != self.pretty_branch_name:
            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Release Debian Packaging",
                factory=self.getReleasePipeline(),
                workernames=self.props['workernames'],
                #NB: We'r enot copying the branch proerty to tag_version as above since this *should not get run automatically*, right?
                properties=dict(prod_props) | {"repo_component": "stable"},
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }DebsTesting"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Debian Testing Packaging Generation",
            change_filter=util.ChangeFilter(category=None, branch_re=f'{ self.props["pkg_major_version"] }\.\d*-\d*'),
            builderNames=[ self.pretty_branch_name + " Testing Debian Packaging" ])

        forceParams = [
            util.CodebaseParameter(
                "",
                label="Build Settings",
                # will generate a combo box
                branch=util.FixedParameter(
                    name="version",
                    default=self.pretty_branch_name,
                ),
                branch=util.FixedParameter(name="branch", default=self.pretty_branch_name),
                # will generate nothing in the form, but revision, repository,
                # and project are needed by buildbot scheduling system so we
                # need to pass a value ("")
                revision=util.FixedParameter(name="revision", default="HEAD"),
                repository=util.FixedParameter(
                    name="repository", default="{{ source_repo_url }}"),
                project=util.FixedParameter(name="project", default=""),
                priority=util.FixedParameter(name="priority", default=0),
            ),
        ]

        params = [
                util.StringParameter(
                    name="tag_version",
                    label="Release tag",
                    default="N.M-1",
                )
            ]

        if "Develop" != self.pretty_branch_name:
            scheds[f"{ self.pretty_branch_name}DebsRelease"] = common.getForceScheduler(
                name=self.pretty_branch_name + "DebsRelease",
                props=self.props,
                codebase=codebase,
                params=params,
                builderNames=[ self.pretty_branch_name + " Release Debian Packaging"])

        return scheds
