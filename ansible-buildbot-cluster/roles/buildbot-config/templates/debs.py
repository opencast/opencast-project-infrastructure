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
        "deb_signing_key_filename"
        ]

    OPTIONAL_PARAMS = [
        "Build"
        ]

    props = {}
    pretty_branch_name = None
    build_sched = None

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

        # Remember, these are the *private* keys
        # For the debian packages, for the repo metadata we use deb_signing_key_*
        self.props["signing_key_filename"] = "{{ signing_key_filename }}"
        self.props["signing_key_id"] = "{{ signing_key_id }}"

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
                        'echo "source library.sh\nSIGNING_KEY=%(prop:signing_key_id)s doOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:branch)s" | tee build.sh'
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
                "SIGNING_KEY": util.Interpolate("%(prop:signing_key_id)s")
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
        f_package_debs.addStep(common.loadSigningKey("%(prop:signing_key_filename)s"))
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


    def notifyMatrix(self, f_package_debs, message="", doStepIf=True, hideStepIf=False):

        notifyMatrix = common.notifyMatrix(
            message=message,
            roomId="{{ default_matrix_room }}",
            warnOnFailure=True,
            flunkOnFailure=False,
            name="Notifying the Releases room",
            doStepIf=doStepIf and message != "",
            hideStepIf=hideStepIf or message == "")

        notifyMatrixProp = common.notifyMatrix(
            message="%(prop:matrix_message)s",
            roomId="{{ default_matrix_room }}",
            warnOnFailure=True,
            flunkOnFailure=False,
            name="Notifying the Releases room",
            doStepIf=doStepIf and util.Property("matrix_message", default="") != "",
            hideStepIf=hideStepIf or util.Property("matrix_message", default="") == "")

        f_package_debs.addStep(notifyMatrix)
        f_package_debs.addStep(notifyMatrixProp)


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


    def publishRepo(self, f_package_debs, s3_target="s3:s3:", access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        debRepoPublish = common.shellCommand(
            command=["./publish-branch", util.Interpolate("%(prop:pkg_major_version)s.x"), s3_target, util.Interpolate("%(prop:deb_signing_key_id)s")],
            name=util.Interpolate("Publishing %(prop:pkg_major_version)s.x on " + s3_target),
            env={
                "AWS_ACCESS_KEY_ID": util.Secret(access_key_secret_id),
                "AWS_SECRET_ACCESS_KEY": util.Secret(secret_key_secret_id)
            },
            locks=repo_lock.access('exclusive'),
            # Yes, 4 hours. Publishing can take a while.
            timeout=4 * 60 * 60)

        f_package_debs.addStep(common.loadSigningKey("%(prop:deb_signing_key_filename)s"))
        f_package_debs.addStep(debRepoPublish)
        f_package_debs.addStep(debsNotifyMatrix)
        f_package_debs.addStep(common.unmountS3fs("/builder/s3/repo/debs"))


    def promotePackage(self, f_package_debs):

        debRepoPromote = common.shellCommand(
            command=["./promote-package", util.Property("pkg_name"), util.Property("tag_version"), util.Interpolate("%(prop:pkg_major_version)s.x"), "testing", "stable"],
            name=util.Interpolate("Promoting %(prop:pkg_name)s in %(prop:branch)s to stable"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        #NB: We are not building debs here, just promoting from test!
        f_package_debs.addStep(debRepoPromote)

        return f_package_debs


    def dropPackage(self, f_package_debs):

        debRepoDropPackage = common.shellCommand(
            command=['./drop-package', util.Interpolate("%(prop:pkg_major_version)s.x"), util.Interpolate("%(prop:repo_component:-unstable)s"), util.Property("pkg_name"), util.Property("tag_version")],
            name=util.Interpolate("Dropping opencast %(prop:tag_version)s from %(prop:repo_component:-unstable)s"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

        f_package_debs.addStep(debRepoDropPackage)


    def syncRepo(self, f_package_debs, access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        #NB: This doesn't know, or care at all about branches.  Sync the full state of the repo, minus the unstable bits
        #NB: Not hiding this step since we want to know we thought about it in non-release cases
        debRepoSync = common.shellCommand(
                command=["./rados-sync"],
                name="Syncing repo state from LITE infra to rados",
                env={
                    'AWS_ACCESS_KEY_ID': util.Secret(access_key_secret_id),
                    'AWS_SECRET_ACCESS_KEY': util.Secret(secret_key_secret_id)
                },
                doStepIf=util.Property("release_build", default="false") == "true",
                locks=repo_lock.access('exclusive'),
                timeout=1200)

        f_package_debs.addStep(debRepoSync)
        f_package_debs.addStep(common.unmountS3fs("/builder/s3/repo/published"))


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

        pubmessage="Opencast %(prop:tag_version)s is now in the Deb %(prop:repo_component)s repo"

        f_package_debs = util.BuildFactory()
        self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="rados")
        self.includeRepo(f_package_debs, s3_target="s3:s3:")
        self.publishRepo(f_package_debs, s3_target="s3:s3:")
        self.notifyMatrix(f_package_debs, pubmessage)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getReleasePipeline(self):

        pubmessage="Opencast %(prop:tag_version)s is now in the Deb %(prop:repo_component)s repo"

        #NB: We are not building debs here, just promoting from test!
        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="rados")
        self.promotePackage(f_package_debs)
        self.publishRepo(f_package_debs, s3_target="s3:s3:")
        self.notifyMatrixf_package_debs, pubmessage)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getPublishPipeline(self):

        #NB: We are not building debs here, just promoting from test!
        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        #NB: The default S3 is LITE, so publish there
        self.publishRepo(f_package_debs, s3_target="s3:loganite:")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getSyncPipeline(self):

        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        #NB: We mount LITE's published file so we can sync between that and rados
        self.mountS3(f_package_debs, host="published")
        self.syncRepo(f_package_debs, access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.notifyMatrix(f_package_debs)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getDropPipeline(self):

        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="rados")
        self.dropPackage(f_package_debs)
        self.publishRepo(f_package_debs, s3_target="s3:s3:")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getBuilders(self):

        builders = []

        deb_props = dict(self.props)
        deb_props['image'] = random.choice({{ docker_debian_worker_images }})
        deb_props['release_build'] = 'false'
        lock = util.MasterLock(f"{ self.props['git_branch_name'] }deb_lock", maxCount=1)

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Deb Pkg Unstable",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames'],
            properties=dict(deb_props) | {"repo_component": "unstable"},
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        prod_props = dict(deb_props)
        prod_props['release_build'] = 'true'

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Deb Pkg Testing",
            factory=self.getTestPipeline(),
            workernames=self.props['workernames'],
            properties=dict(prod_props) | {"repo_component": "testing", "tag_version": util.Property('branch')},
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Deb Publish",
            factory=self.getPublishPipeline(),
            workernames=self.props['workernames'],
            properties=dict(prod_props) | {"tag_version": util.Property('branch')},
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Deb Drop Release",
            factory=self.getDropPipeline(),
            workernames=self.props['workernames'],
            properties=prod_props,
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        if "Develop" != self.pretty_branch_name:

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Deb Promote Release",
                factory=self.getReleasePipeline(),
                workernames=self.props['workernames'],
                #NB: We'r enot copying the branch proerty to tag_version as above since this *should not get run automatically*, right?
                properties=dict(prod_props) | {"repo_component": "stable" },
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }DebsTesting"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Debian Testing Packaging",
            change_filter=util.ChangeFilter(repository=["https://code.loganite.ca/opencast/debian-packaging.git", "git@code.loganite.ca:opencast/debian-packaging.git"], branch_re=f'{ self.props["pkg_major_version"] }\.\d*-\d*'),
            builderNames=[ self.pretty_branch_name + " Deb Pkg Testing" ])

        codebase = [
            util.CodebaseParameter(
                "",
                label="Build Settings",
                # will generate a combo box
                branch=util.StringParameter(name="branch", default=util.Interpolate("%(prop:pkg_major_version)s.x")),
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
            ),
            util.StringParameter(
                name="pkg_name",
                label="Package name",
                default="opencast",
            )
        ]

        if "Develop" != self.pretty_branch_name:
            scheds[f"{ self.pretty_branch_name}DebsTest"] = common.getForceScheduler(
                name=self.pretty_branch_name + "DebsTest",
                props=self.props,
                codebase=codebase,
                params=params,
                builderNames=[ self.pretty_branch_name + " Deb Pkg Testing" ])

            scheds[f"{ self.pretty_branch_name}DebsPromote"] = common.getForceScheduler(
                name=self.pretty_branch_name + "DebsPromote",
                props=self.props,
                codebase=codebase,
                params=params,
                builderNames=[ self.pretty_branch_name + " Deb Promote Release" ])

        scheds[f"{ self.pretty_branch_name}DebsDrop"] = common.getForceScheduler(
            name=self.pretty_branch_name + "DebsDrop",
            props=self.props,
            codebase=codebase,
            params=params,
            builderNames=[ self.pretty_branch_name + " Deb Drop Release" ])

        scheds[f"{ self.pretty_branch_name}DebsPubForce"] = common.getForceScheduler(
            name=self.pretty_branch_name + "DebsPubForce",
            props=self.props,
            codebase=codebase,
            builderNames=[ self.pretty_branch_name + " Deb Publish" ])

        return scheds
