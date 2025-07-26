# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers

import common
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

    debsClone = steps.Git(
        repourl="{{ source_deb_repo_url }}",
        branch=util.Property('branch'),
        alwaysUseLatest=True,
        mode="full",
        method="fresh",
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Cloning deb packaging configs")

    debsVersion = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="deb_script_rev",
        flunkOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get Debian script revision")

    def __init__(self, props):
        for key in Debs.REQUIRED_PARAMS:
            if key not in props:
                pass
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

        # Override the branch property with the pkg_version.  This needs to run PRIOR to clone.
        # This is used for the FORCE schedulers since they don't have the branch value set correctly, but *do* have the pkg_version set right.
        debBranchOverride = steps.SetProperty(
            property="branch",
            value=util.Property("pkg_version"),
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "true" and step.getProperty("pkg_version", default="") != "",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "false" or step.getProperty("pkg_version", default="") == "",
            name="Set branch variable based on pkg_verison variable")

        #This runs after the clone
        debsSetMinor = steps.SetPropertyFromCommand(
            command=util.Interpolate("echo %(prop:branch)s | cut -f 2 -d '.' | cut -f 1 -d '-'"),
            property="pkg_minor_version",
            flunkOnFailure=True,
            haltOnFailure=True,
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "true",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "false",
            name="Set minor version property")

        # This sets pkg_version == branch, for release builds.
        # This is needed for builds where the branch is set right but the pkg_version is missing - ie, push events
        debsSetPkgVersion = steps.SetProperty(
            property="pkg_version",
            value=util.Interpolate("%(prop:branch)s"),
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "true" and step.getProperty("pkg_version", default="") != "",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "false" or step.getProperty("pkg_version", default="") == "",
            name="Calculate expected build version")

        # This sets pkg_version for non-release builds
        debsCalcVersion = steps.SetProperty(
            property="pkg_version",
            value=util.Interpolate("%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s-%(prop:buildnumber)s-%(prop:short_revision)s"),
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "false",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "true",
            name="Calculate expected build version")

        removeSymlinks = common.shellCommand(
            command=['rm', '-rf', 'outputs'],
            name="Prep cloned repo for CI use")

        debsCheckS3 = common.checkAWS(
            path="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            name="Checking that build exists in S3",
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "false",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "true")

        debsFetchFromS3 = common.syncAWS(
            pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            pathTo="binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/",
            name="Fetch build from S3",
            doStepIf=lambda step: step.getProperty("release_build", default="false") != "true",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "true")

        debsFetchFromGitHub = common.shellCommand(
            command=["./fetch.sh", util.Interpolate("%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s")],
            workdir="build/binaries",
            name="Fetch release build from GitHub",
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "true",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") != "true")

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
            doStepIf=lambda step: step.getProperty("release_build", default="false") != "true",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "true")

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
            doStepIf=lambda step: step.getProperty("release_build", default="false") == "true",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") != "true")

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
        # This step overrides the branch value, so must run prior to clone!
        f_package_debs.addStep(debBranchOverride)
        f_package_debs.addStep(self.debsClone)
        # Set the debian packaging version as deb_script_rev
        f_package_debs.addStep(self.debsVersion)
        # Set got_revision to the latest Opencast build version
        f_package_debs.addStep(common.getLatestBuildRevision(
            doStepIf=lambda step: step.getProperty("release_build", default="false") != "true",
            hideStepIf=lambda _, step: step.getProperty("release_build", default="false") == "true"))
        # Get a short hash of the aboev with cut -c
        f_package_debs.addStep(common.getShortBuildRevision())
        # Calculate the pkg_version value from the above variables, for non-release builds
        f_package_debs.addStep(debsCalcVersion)
        # Set the minor version, for release builds
        f_package_debs.addStep(debsSetMinor)
        # Set pkg_version to equal the branch variable, for release builds
        f_package_debs.addStep(debsSetPkgVersion)
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


    def addTobiraBuild(self, f_package_debs):

        removeSymlinks = common.shellCommand(
            command=['rm', '-rf', 'outputs'],
            name="Prep cloned repo for CI use")

        fetchTobiraFromGitHub = common.shellCommand(
            command=["./tobira-fetch.sh", util.Interpolate("%(prop:pkg_version)s")],
            workdir="build/binaries",
            name="Fetch Tobira release build from GitHub")

        buildTobira = common.shellSequence(
            commands=[
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\nSIGNING_KEY=%(prop:signing_key_id)s doTobira %(prop:pkg_version)s %(prop:branch)s %(prop:deb_version)s" | tee build.sh'
                    ),
                    logname='write'),
                common.shellArg(
                    command=['bash', 'build.sh'],
                    logname='build')
            ],
            env={
                "NAME": "Buildbot",
                "EMAIL": "buildbot@{{ groups['master'][0] }}",
                "SIGNING_KEY": util.Interpolate("%(prop:deb_signing_key_id)s")
            },
            name="Build Tobira")

        f_package_debs.addStep(common.getPreflightChecks())
        f_package_debs.addStep(self.debsClone)
        f_package_debs.addStep(self.debsVersion)
        f_package_debs.addStep(removeSymlinks)
        f_package_debs.addStep(fetchTobiraFromGitHub)
        #NB: This can be either the default, or the per-branch depending on the *buidler* below
        f_package_debs.addStep(common.loadSigningKey())
        f_package_debs.addStep(buildTobira)
        #We unload here since we *might* be using a different key in a minute to sign the actual repo
        f_package_debs.addStep(common.unloadSigningKey())


    def addWhisperBuild(self, f_package_debs):

        removeSymlinks = common.shellCommand(
            command=['rm', '-rf', 'outputs'],
            name="Prep cloned repo for CI use")

        fetchWhisperFromGithub = common.shellCommand(
            command=["./whisper-fetch.sh", util.Interpolate("%(prop:pkg_version)s")],
            workdir="build/binaries",
            name="Fetch Whisper release build from GitHub")

        buildWhisper = common.shellSequence(
            commands=[
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\nSIGNING_KEY=%(prop:signing_key_id)s doWhisper %(prop:pkg_version)s %(prop:branch)s %(prop:deb_version)s" | tee build.sh'
                    ),
                    logname='write'),
                common.shellArg(
                    command=['bash', 'build.sh'],
                    logname='build')
            ],
            env={
                "NAME": "Buildbot",
                "EMAIL": "buildbot@{{ groups['master'][0] }}",
                "SIGNING_KEY": util.Interpolate("%(prop:deb_signing_key_id)s")
            },
            timeout=2400,
            name="Build Whisper")

        f_package_debs.addStep(common.getPreflightChecks())
        f_package_debs.addStep(self.debsClone)
        f_package_debs.addStep(self.debsVersion)
        f_package_debs.addStep(removeSymlinks)
        f_package_debs.addStep(fetchWhisperFromGithub)
        #NB: This can be either the default, or the per-branch depending on the *buidler* below
        f_package_debs.addStep(common.loadSigningKey())
        f_package_debs.addStep(buildWhisper)
        #We unload here since we *might* be using a different key in a minute to sign the actual repo
        f_package_debs.addStep(common.unloadSigningKey())


    def addFfmpegBuild(self, f_package_debs):

        removeSymlinks = common.shellCommand(
            command=['rm', '-rf', 'outputs'],
            name="Prep cloned repo for CI use")

        fetchFfmpeg = common.shellCommand(
            command=["./ffmpeg-fetch.sh", util.Property("pkg_version")],
            workdir="build/binaries",
            name="Fetch ffmpeg build from s3")

        buildFfmpeg = common.shellSequence(
            commands=[
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\nSIGNING_KEY=%(prop:signing_key_id)s doFfmpeg %(prop:pkg_version)s amd64 %(prop:branch)s ffmpeg-%(prop:pkg_version)s-amd64 %(prop:deb_version)s" | tee build.sh'
                    ),
                    logname='amd64'),
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\nSIGNING_KEY=%(prop:signing_key_id)s doFfmpeg %(prop:pkg_version)s arm64 %(prop:branch)s ffmpeg-%(prop:pkg_version)s-arm64 %(prop:deb_version)s" | tee -a build.sh'
                    ),
                    logname='arm64'),
                common.shellArg(
                    command=['bash', 'build.sh'],
                    logname='build')
            ],
            env={
                "NAME": "Buildbot",
                "EMAIL": "buildbot@{{ groups['master'][0] }}",
                "SIGNING_KEY": util.Interpolate("%(prop:deb_signing_key_id)s")
            },
            name="Build ffmpeg")

        f_package_debs.addStep(common.getPreflightChecks())
        f_package_debs.addStep(self.debsClone)
        f_package_debs.addStep(self.debsVersion)
        f_package_debs.addStep(removeSymlinks)
        f_package_debs.addStep(fetchFfmpeg)
        #NB: This can be either the default, or the per-branch depending on the *buidler* below
        f_package_debs.addStep(common.loadSigningKey())
        f_package_debs.addStep(buildFfmpeg)
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


    def mountS3(self, f_package_debs, host="loganite", access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        f_package_debs.addStep(common.shellCommand(
            command=[f'./mount.{ host }'],
            env={
                'AWSACCESSKEYID': util.Secret(access_key_secret_id),
                'AWSSECRETACCESSKEY': util.Secret(secret_key_secret_id)
            },
            name=f"Mounting { host } S3"))


    def notifyMatrix(self, f_package_debs, message="", lite_message=""):

        notifyMatrix = common.notifyMatrix(
            message=message,
            roomId="{{ default_matrix_room }}",
            warnOnFailure=True,
            flunkOnFailure=False,
            name="Notifying the Releases room",
            doStepIf=lambda step: message != "" and step.getProperty("pkg_name") == "opencast",
            hideStepIf=message == "")

        notifyMatrixLite = common.notifyMatrix(
            message=lite_message,
            roomId="!AaWaUyuMWuqAWaUFsK:matrix.org",
            secretId="lite_announce_secret",
            warnOnFailure=True,
            flunkOnFailure=False,
            name="Notifying the LITE Releases room",
            doStepIf=lambda step: lite_message != "" and step.getProperty("pkg_name") == "opencast",
            hideStepIf=lite_message == "")

        f_package_debs.addStep(notifyMatrix)
        f_package_debs.addStep(notifyMatrixLite)


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

        f_package_debs.addStep(debRepoCreate)
        f_package_debs.addStep(debRepoIngest)


    def snapshotCleanup(self, f_package_debs, s3_target="s3:s3"):

        debSnapshotCleanup = common.shellCommand(
            command=["./snapshot-cleanup", util.Interpolate("%(prop:pkg_major_version)s.x"), s3_target],
            name=util.Interpolate(f"%(prop:pkg_major_version)s.x repository snapshot cleanup"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

        debRepoPrune = common.shellCommand(
            command=["./clean-unstable-repo", util.Interpolate("%(prop:pkg_major_version)s.x"), util.Property("max_left")],
            name=util.Interpolate(f"Pruning %(prop:pkg_major_version)s.x unstable repository"),
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60)

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
        f_package_debs.addStep(common.unmountS3fs("/builder/s3/repo/debs"))


    def promotePackage(self, f_package_debs):

        debRepoPromote = common.shellCommand(
            command=["./promote-package", util.Property("pkg_name"), util.Property("pkg_version"), util.Interpolate("%(prop:pkg_major_version)s.x"), "testing", "stable"],
            name=util.Interpolate("Promoting %(prop:pkg_name)s in %(prop:branch)s to stable"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        #NB: We are not building debs here, just promoting from test!
        f_package_debs.addStep(debRepoPromote)

        return f_package_debs


    def copyPackage(self, f_package_debs):

        debRepoCopy = common.shellCommand(
                command=["./copy-package", util.Property("pkg_name"), util.Property("pkg_version"), util.Interpolate("%(prop:from_branch)s.x"), util.Interpolate("%(prop:to_branch)s.x"), util.Property("from_component"), util.Property("to_component")],
            name=util.Interpolate("Copying %(prop:pkg_name)s %(prop:pkg_version)s"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        #NB: We are not building debs here, just copying
        f_package_debs.addStep(debRepoCopy)

        return f_package_debs

    def dropPackage(self, f_package_debs):

        debRepoDropPackage = common.shellCommand(
            command=['./drop-package', util.Interpolate("%(prop:pkg_major_version)s.x"), util.Interpolate("%(prop:repo_component:-unstable)s"), util.Property("pkg_name"), util.Property("pkg_version")],
            name=util.Interpolate("Drop %(prop:pkg_name)s from %(prop:pkg_major_version)s.x %(prop:repo_component:-unstable)s"),
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
                doStepIf=lambda step: step.getProperty("release_build", default="false") == "true",
                locks=repo_lock.access('exclusive'),
                timeout=1200)

        #NB: We mount LITE's published file so we can sync between that and rados
        self.mountS3(f_package_debs, host="published")
        f_package_debs.addStep(debRepoSync)
        f_package_debs.addStep(common.unmountS3fs("/builder/s3/repo/published"))


    def cleanup(self, f_package_debs):

        f_package_debs.addStep(common.unloadSigningKey())
        f_package_debs.addStep(common.cleanupS3Secrets())
        f_package_debs.addStep(common.getClean())


    def getBuildPipeline(self, buildType="oc"):

        lite_message = "DEB: %(prop:pkg_name)s %(prop:pkg_version)s in %(prop:pkg_major_version)s.x %(prop:repo_component)s"

        f_package_debs = util.BuildFactory()
        if "ffmpeg" == buildType:
            self.addFfmpegBuild(f_package_debs)
        elif "tobira" == buildType:
            self.addTobiraBuild(f_package_debs)
        elif "whisper" == buildType:
            self.addWhisperBuild(f_package_debs)
        else:
            self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        self.includeRepo(f_package_debs, s3_target="s3:loganite:")
        self.snapshotCleanup(f_package_debs, s3_target="s3:loganite:")
        self.publishRepo(f_package_debs, s3_target="s3:loganite:")
        self.notifyMatrix(f_package_debs, lite_message=lite_message)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getCleanupPipeline(self):

        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        self.snapshotCleanup(f_package_debs, s3_target="s3:loganite:")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getTestPipeline(self):

        lite_message = "DEB: %(prop:pkg_name)s %(prop:pkg_version)s in %(prop:pkg_major_version)s.x %(prop:repo_component)s"
        matrix_message = "%(prop:pkg_name)s %(prop:pkg_version)s now in Deb %(prop:repo_component)s repo"

        f_package_debs = util.BuildFactory()
        self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        self.includeRepo(f_package_debs, s3_target="s3:loganite:")
        self.snapshotCleanup(f_package_debs, s3_target="s3:loganite:")
        #NB: The default S3 is LITE, so publish there
        self.publishRepo(f_package_debs, s3_target="s3:loganite:")
        self.notifyMatrix(f_package_debs, lite_message=lite_message)
        self.syncRepo(f_package_debs, access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.notifyMatrix(f_package_debs, message=matrix_message)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getPromotePipeline(self):

        lite_message = "DEB: %(prop:pkg_name)s %(prop:pkg_version)s in %(prop:pkg_major_version)s.x %(prop:repo_component)s"
        matrix_message = "%(prop:pkg_name)s %(prop:pkg_version)s now in Deb %(prop:repo_component)s repo"
        #NB: We are not building debs here, just promoting from test!
        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        self.promotePackage(f_package_debs)
        #NB: The default S3 is LITE, so publish there
        self.publishRepo(f_package_debs, s3_target="s3:loganite:")
        self.notifyMatrix(f_package_debs, lite_message=lite_message)
        self.syncRepo(f_package_debs, access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.notifyMatrix(f_package_debs, message=matrix_message)
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


    def getCopyPipeline(self):

        #NB: We are not building debs here, just promoting from test!
        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        self.copyPackage(f_package_debs)
        f_package_debs.addStep(
            steps.SetProperty(
                property="pkg_major_version",
                value=util.Property("to_branch"),
                flunkOnFailure=True,
                haltOnFailure=True,
                name="Set major version property"))
        #NB: The default S3 is LITE, so publish there
        self.publishRepo(f_package_debs, s3_target="s3:loganite:")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getSyncPipeline(self):

        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.syncRepo(f_package_debs, access_key_secret_id="rados.access_key", secret_key_secret_id="rados.secret_key")
        self.cleanup(f_package_debs)

        return f_package_debs


    def getDropPipeline(self):

        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs, host="loganite")
        f_package_debs.addStep(
            steps.SetPropertyFromCommand(
                command=util.Interpolate("echo %(prop:repo_branch)s | cut -f 1 -d '.'"),
                property="pkg_major_version",
                flunkOnFailure=True,
                haltOnFailure=True,
                name="Set major version property"))
        self.dropPackage(f_package_debs)
        #NB: The default S3 is LITE, so publish there
        self.publishRepo(f_package_debs, s3_target="s3:loganite:")
        self.cleanup(f_package_debs)

        return f_package_debs


    @util.renderer
    def pickRandomDebImage(self):
        return random.choice({{ docker_debian_worker_images }})


    def getBuilders(self):

        builders = []

        deb_props = dict(self.props)
        deb_props['image'] = self.pickRandomDebImage
        deb_props['release_build'] = 'false'

        lock = util.MasterLock(f"{ self.props['git_branch_name'] }deb_lock", maxCount=1)

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Deb Pkg Unstable",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames'],
            properties=dict(deb_props) | {"repo_component": "unstable", "branch": self.props['git_branch_name'] },
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        prod_props = dict(deb_props)
        prod_props['release_build'] = 'true'

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Deb Publish",
            factory=self.getPublishPipeline(),
            workernames=self.props['workernames'],
            properties=dict(prod_props),
            collapseRequests=True,
            locks=[lock.access('exclusive')]))


        if "Develop" != self.pretty_branch_name:
            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Deb Pkg Testing",
                factory=self.getTestPipeline(),
                workernames=self.props['workernames'],
                # Setting tag_version here from the branch, which is something like N.M-O
                properties=dict(prod_props) | {"repo_component": "testing"},
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Deb Promote Release",
                factory=self.getPromotePipeline(),
                workernames=self.props['workernames'],
                # tag_version set in the scheduler props below
                properties=dict(prod_props) | {"repo_component": "stable" },
                collapseRequests=True,
                locks=[lock.access('exclusive')]))
        else:
            builders.append(util.BuilderConfig(
                name="Deb Drop Release",
                factory=self.getDropPipeline(),
                workernames=self.props['workernames'],
                properties=prod_props,
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

            builders.append(util.BuilderConfig(
                name="Deb Repo Sync",
                factory=self.getSyncPipeline(),
                workernames=self.props['workernames'],
                properties=prod_props,
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

            builders.append(util.BuilderConfig(
                name="Deb Repo Copy",
                factory=self.getCopyPipeline(),
                workernames=self.props['workernames'],
                properties=prod_props,
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

            builders.append(util.BuilderConfig(
                name="Deb Repo Cleanup",
                factory=self.getCleanupPipeline(),
                workernames=self.props['workernames'],
                properties=prod_props,
                collapseRequests=True,
                locks=[lock.access('exclusive')]))

            #We only provide this for develop.  Use the promote/copy builder to spread the resulting files around
            for buildtype in [ "ffmpeg", "tobira", "whisper" ]:
                builders.append(util.BuilderConfig(
                    name=f"{ buildtype.capitalize() } Pkg Testing",
                    factory=self.getBuildPipeline(buildtype),
                    workernames=self.props['workernames'],
                    properties=dict(prod_props) | {"repo_component": "testing", "pkg_name": buildtype},
                    collapseRequests=True,
                    locks=[lock.access('exclusive')]))

        return builders


    def getSchedulers(self):

        scheds = {}

        codebase = [
            util.CodebaseParameter(
                "",
                label="Build Settings",
                # will generate a combo box
                branch=util.FixedParameter(name="branch", default=self.props['git_branch_name']),
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
            util.FixedParameter(
                name="pkg_name",
                label="Package name",
                default="opencast"),
            util.StringParameter(
                name="pkg_version",
                label="Package Version",
                default="N.M-Z")
        ]

        if "Develop" != self.pretty_branch_name:
            # Regular builds
            scheds[f"{self.pretty_branch_name}DebsTesting"] = common.getAnyBranchScheduler(
                name=self.pretty_branch_name + " Debian Testing Packaging",
                change_filter=util.ChangeFilter(repository=["https://code.loganite.ca/opencast/debian-packaging.git", "git@code.loganite.ca:opencast/debian-packaging.git"], branch_re=f'{self.props["pkg_major_version"]}\.\d*-\d*'),
                properties=self.props,
                builderNames=[self.pretty_branch_name + " Deb Pkg Testing"])

            scheds[f"{self.pretty_branch_name}DebsTest"] = common.getForceScheduler(
                name=self.pretty_branch_name + "DebsTest",
                props=self.props,
                codebase=codebase,
                params=params,
                builderNames=[self.pretty_branch_name + " Deb Pkg Testing"])

            scheds[f"{self.pretty_branch_name}DebsPromote"] = common.getForceScheduler(
                name=self.pretty_branch_name + "DebsPromote",
                props=self.props,
                codebase=codebase,
                params=params,
                builderNames=[self.pretty_branch_name + " Deb Promote Release"])

        else:
            # We only provide this for develop.  Use the promote/copy builder to spread the resulting files around
            for buildtype in ["ffmpeg", "tobira", "whisper"]:
                toolparams = [
                    util.FixedParameter(
                        name="pkg_name",
                        label="Package name",
                        default=buildtype),
                    util.StringParameter(
                        name="pkg_version",
                        label="Release tag",
                        default="N.M"),
                    util.StringParameter(
                        name="deb_version",
                        label="Package version",
                        default="1")
                ]
                scheds[f"{buildtype}Build"] = common.getForceScheduler(
                    name=self.pretty_branch_name + f"{buildtype}Build",
                    props=self.props,
                    codebase=codebase,
                    params=toolparams,
                    builderNames=[f"{buildtype.capitalize()} Pkg Testing"])

            scheds["DebsSyncForce"] = common.getForceScheduler(
                name="DebsSyncForce",
                props=self.props,
                codebase=codebase,
                builderNames=["Deb Repo Sync"])
            scheds["DebsSync"] = schedulers.Triggerable(
                name="Debian Repository Sync",
                builderNames=["Deb Repo Sync"])

            scheds["DebsCopyForce"] = common.getForceScheduler(
                name="DebsCopyForce",
                props=self.props,
                codebase=codebase,
                params=[
                    util.StringParameter(
                        name="pkg_name",
                        label="Package name"),
                    util.StringParameter(
                        name="pkg_version",
                        label="Package version",
                        default="N.M-1"),
                    util.StringParameter(
                        name="from_component",
                        label="Copy from component",
                        default="unstable"),
                    util.StringParameter(
                        name="from_branch",
                        label="Copy from branch",
                        default="eg: 17, NOT 17.x"),
                    util.StringParameter(
                        name="to_component",
                        label="Copy to component",
                        default="unstable"),
                    util.StringParameter(
                        name="to_branch",
                        label="Copy to branch",
                        default="eg: 18, NOT 18.x")
                ],
                builderNames=["Deb Repo Copy"])

            scheds["DebsDrop"] = common.getForceScheduler(
                name="DebsDrop",
                props=self.props,
                codebase=codebase,
                params=[
                    util.StringParameter(
                        name="repo_branch",
                        label="Repository branch",
                        default=self.props['pkg_major_version'] + ".x"),
                    util.StringParameter(
                        name="pkg_name",
                        label="Package name"),
                    util.StringParameter(
                        name="pkg_version",
                        label="Version",
                        default="N.M-Z"),
                    util.StringParameter(
                        name="repo_component",
                        label="Repo Component",
                        default="unstable")
                ],
                builderNames=["Deb Drop Release"])

            scheds["DebsCleanup"] = common.getForceScheduler(
                name="DebsCleanup",
                props=self.props,
                codebase=codebase,
                params=[
                    util.StringParameter(
                        name="repo_branch",
                        label="Repository branch",
                        default=self.props['pkg_major_version'] + ".x"),
                    util.StringParameter(
                        name="max_left",
                        label="Maximum number of unstable versions left",
                        default="5")
                ],
                builderNames=["Deb Repo Cleanup"])

        #THis is the bacikup force-publish scheduler.  Keeping just inc ase we end up with damaged publish states - this can force a refresh.
        scheds[f"{self.pretty_branch_name}DebsPubForce"] = common.getForceScheduler(
            name=self.pretty_branch_name + "DebsPubForce",
            props=self.props,
            codebase=codebase,
            builderNames=[self.pretty_branch_name + " Deb Publish"])


        return scheds
