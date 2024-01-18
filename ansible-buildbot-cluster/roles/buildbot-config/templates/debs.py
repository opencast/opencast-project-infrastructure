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
        "workernames"
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
        if 'signing_key' not in self.props:
            self.props['signing_key'] = "{{ hostvars[inventory_hostname]['signing_key_id'] }}"


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
            doStepIf=True, #util.Property("release_build", default=False),
            hideStepIf=False, #not util.Property("release_build", default=False))
            name="Set minor version property")

        debsVersion = steps.SetPropertyFromCommand(
            command="git rev-parse HEAD",
            property="deb_script_rev",
            flunkOnFailure=True,
            haltOnFailure=True,
            workdir="build",
            name="Get Debian script revision")

        removeSymlinks = common.shellCommand(
            command=['rm', '-rf', 'outputs'],
            name="Prep cloned repo for CI use")

        debsFetchFromS3 = common.syncAWS(
            pathFrom="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
            pathTo="binaries/%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s/",
            name="Fetch build from S3",
            doStepIf=not util.Property("release_build", default=False),
            hideStepIf=util.Property("release_build", default=False))

        debsFetchFromGitHub = common.shellCommand(
            command=["./fetch.sh", util.Interpolate("%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s")],
            workdir="build/binaries",
            name="Fetch release build from GitHub",
            doStepIf=util.Property("release_build", default=False),
            hideStepIf=not util.Property("release_build", default=False))

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
                        'echo "source library.sh\ndoOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:got_revision)s" | tee build.sh'
                    ),
                    logname='write'),
            ],
            env={
                "NAME": "Buildbot",
                "EMAIL": "buildbot@{{ groups['master'][0] }}",
                "SIGNING_KEY": util.Interpolate("%(prop:signing_key)s")
            },
            name="Prep to build debs",
            doStepIf=not util.Property("release_build", default=False),
            hideStepIf=util.Property("release_build", default=False))

        debsPrepReleaseBuild = common.shellSequence(
            commands=[
                common.shellArg(
                    command=util.Interpolate(
                        'ln -s opencast-%(prop:pkg_major_version)s_%(prop:pkg_major_version)s.%(prop:pkg_minor_version)s.orig.tar.xz opencast-%(prop:pkg_major_version)s_%(prop:branch)s.orig.tar.xz && ls'
                    ),
                    logname='link'),
                common.shellArg(
                    command=util.Interpolate(
                        'echo "source library.sh\ndoOpencast %(prop:pkg_major_version)s.%(prop:pkg_minor_version)s %(prop:branch)s %(prop:branch)s" | tee build.sh'
                    ),
                    logname='write'),
            ],
            name="Prep to build release debs",
            doStepIf=util.Property("release_build", default=False),
            hideStepIf=not util.Property("release_build", default=False))

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
                "SIGNING_KEY": util.Interpolate("%(prop:signing_key)s")
            },
            name="Build debs")

        f_package_debs.addStep(common.getPreflightChecks())
        f_package_debs.addStep(debsClone)
        f_package_debs.addStep(debsSetMinor)
        f_package_debs.addStep(debsVersion)
        f_package_debs.addStep(common.getLatestBuildRevision())
        f_package_debs.addStep(common.getShortBuildRevision())
        f_package_debs.addStep(removeSymlinks)
        f_package_debs.addStep(debsFetchFromS3)
        f_package_debs.addStep(debsFetchFromGitHub)
        f_package_debs.addStep(common.loadSigningKey())
        f_package_debs.addStep(debsPrepBuild)
        f_package_debs.addStep(debsPrepReleaseBuild)
        f_package_debs.addStep(debsBuild)


    def setupRepo(self, f_package_debs):

        debRepoClone = common.getClone(url="{{ source_deb_packaging_repo_url }}",
                              branch="{{ deb_packaging_repo_branch }}",
                              name="Cloning deb repo configs")

        debRepoLoadKeys = common.shellCommand(
            command=['./build-keys'],
            name="Loading repo sig verification keys")

        f_package_debs.addStep(debRepoClone)
        f_package_debs.addStep(debRepoLoadKeys)


    def mountS3(self, f_package_debs, host="{{ s3_host }}", access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        f_package_debs.addStep(
            common.mountS3fs(
                host=host,
                access_key_secret_id=access_key_secret_id,
                secret_key_secret_id=secret_key_secret_id))


    def includeRepo(self, f_package_debs):

        debRepoCreate = common.shellCommand(
            command=['./create-branch', util.Interpolate("%(prop:pkg_major_version)s.x")],
            name=util.Interpolate("Ensuring %(prop:pkg_major_version)s.x repos exist"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        debRepoIngest = common.shellCommand(
                command=['./include-binaries', util.Interpolate("%(prop:pkg_major_version)s.x"), util.Interpolate("%(prop:repo_component:-unstable)s"), util.Interpolate("outputs/%(prop:deb_script_rev)s/*.changes")],
            name=util.Interpolate(f"Adding build to %(prop:repo_component:-unstable)s"),
            locks=repo_lock.access('exclusive'),
            timeout=1800)

        debRepoPrune = common.shellCommand(
            command=util.Interpolate("./snapshot-cleanup %(prop:pkg_major_version)s.x oc && ./clean-unstable-repo %(prop:pkg_major_version)s.x"),
            name=util.Interpolate(f"Pruning %(prop:pkg_major_version)s.x unstable repository"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        f_package_debs.addStep(debRepoCreate)
        f_package_debs.addStep(debRepoIngest)
        f_package_debs.addStep(debRepoPrune)


    def publishRepo(self, f_package_debs, repo="Testing", s3_target="s3:s3:", access_key_secret_id="s3.public_access_key", secret_key_secret_id="s3.public_secret_key"):

        debRepoPublish = common.shellCommand(
                command=["./publish-branch", util.Interpolate("%(prop:pkg_major_version)s.x"), s3_target, util.Interpolate("%(prop:repo_signing_key)s")],
            name=util.Interpolate("Publishing %(prop:pkg_major_version)s.x on " + s3_target),
            env={
                "AWS_ACCESS_KEY_ID": util.Secret(access_key_secret_id),
                "AWS_SECRET_ACCESS_KEY": util.Secret(secret_key_secret_id)
            },
            locks=repo_lock.access('exclusive'),
            timeout=4 * 60 * 60) #Yes, 4 hours.  Publishing from LITE to RADOS can take a *long* time.

        debsNotifyMatrix = common.notifyMatrix(
            message="Opencast %(prop:branch)s is now in the Deb " + repo + " repo",
            roomId="{{ default_matrix_room }}",
            warnOnFailure=True,
            flunkOnFailure=False,
            doStepIf=util.Property("release_build", default=False),
            hideStepIf=not util.Property("release_build", default=False))

        f_package_debs.addStep(debRepoPublish)
        f_package_debs.addStep(debsNotifyMatrix)
        f_package_debs.addStep(common.unmountS3fs())


    def cleanup(self, f_package_debs):

        f_package_debs.addStep(common.unloadSigningKey())
        f_package_debs.addStep(common.cleanupS3Secrets())
        f_package_debs.addStep(common.getClean())


    def getBuildPipeline(self):


        f_package_debs = util.BuildFactory()
        self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs)
        self.includeRepo(f_package_debs)
        self.publishRepo(f_package_debs)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getTestPipeline(self):

        f_package_debs = util.BuildFactory()
        self.addDebBuild(f_package_debs)
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs)
        self.includeRepo(f_package_debs)
        self.publishRepo(f_package_debs)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getReleasePipeline(self):

        debRepoPromote = common.shellCommand(
                command=["./promote-package", "opencast", util.Property("branch"), util.Interpolate("%(prop:pkg_major_version)s.x"), "testing", "stable"],
                name=util.Interpolate("Promoting %(prop:branch)s to stable"),
            locks=repo_lock.access('exclusive'),
            timeout=300)

        #NB: We are not building debs here, just promoting from test!
        f_package_debs = util.BuildFactory()
        self.setupRepo(f_package_debs)
        self.mountS3(f_package_debs)
        f_package_debs.addStep(debRepoPromote)
        self.publishRepo(f_package_debs)
        self.cleanup(f_package_debs)

        return f_package_debs


    def getBuilders(self):

        builders = []

        deb_props = dict(self.props)
        deb_props['image'] = random.choice({{ docker_debian_worker_images }})
        lock = util.MasterLock(f"{ self.props['git_branch_name'] }deb_lock", maxCount=1)

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Debian Packaging",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames'],
            properties=deb_props,
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Testing Debian Packaging",
            factory=self.getTestPipeline(),
            workernames=self.props['workernames'],
            properties=dict(deb_props) | {"release_build": True},
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        builders.append(util.BuilderConfig(
            name=self.pretty_branch_name + " Release Debian Packaging",
            factory=self.getReleasePipeline(),
            workernames=self.props['workernames'],
            properties=dict(deb_props) | {"release_build": True},
            collapseRequests=True,
            locks=[lock.access('exclusive')]))

        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }DebsTesting"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Debian Testing Packaging Generation",
            #FIXME: Set appropriate props (specifically pkg_release_version)
            change_filter=util.ChangeFilter(category=None, branch_re=f'{ self.props["pkg_major_version"] }\.\d*-\d*'),
            builderNames=[ self.pretty_branch_name + " Testing Debian Packaging" ])

        scheds[f"{ self.pretty_branch_name}DebsRelease"] = common.getForceScheduler(
            name=self.pretty_branch_name + "DebsRelease",
            props=self.props,
            builderNames=[ self.pretty_branch_name + " Release Debian Packaging"])

        return scheds
