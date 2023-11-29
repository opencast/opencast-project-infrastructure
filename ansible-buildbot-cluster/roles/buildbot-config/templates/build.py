# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
import common

class Build():

    REQUIRED_PARAMS = [
        "git_branch_name",
        "pkg_major_version",
        "ffmpeg",
        "cores",
        "branch_pretty",
        "jdk",
        "workernames"
        ]

    OPTIONAL_PARAMS = [
        "deploy_env"
        ]

    props = {}
    jdks = []
    pretty_branch_name = None
    buildFilter = None

    def __init__(self, props):
        for key in Build.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Build.OPTIONAL_PARAMS:
            if key in props:
                self.props[key] = props[key]

        self.pretty_branch_name = self.props["branch_pretty"]
        self.jdks = self.props["jdk"]
        self.deploy_env = self.props["deploy_env"] if "deploy_env" in self.props else None
        self.buildFilter = lambda change: any(map(lambda filename: "modules" in filename, change.files)) or any(map(lambda filename: "assemblies" in filename, change.files))

    getBuildSize = common.shellCommand(
        command=['du', '-ch'],
        name='Getting current build dir size')

    uploadTarballs = common.syncAWS(
        pathFrom="build",
        pathTo="s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}",
        name="Upload build to S3")


    def _getBasePipeline(self):

        f_build = util.BuildFactory()
        f_build.addStep(common.getPreflightChecks())
        f_build.addStep(common.getClone())
        f_build.addStep(common.setLocale())
        f_build.addStep(common.setTimezone())

        return f_build


    def getPullRequestPipeline(self):

        f_build = self._getBasePipeline()
        f_build.addStep(common.getWorkerPrep())
        f_build.addStep(common.getBuild())
        f_build.addStep(self.getBuildSize)
{% if push_prs | default(False) %}
        f_build.addStep(common.getTarballs())
        f_build.addStep(self.uploadTarballs)
{% endif %}
        f_build.addStep(common.getClean())

        return f_build


    def getBuildPipeline(self):

        stampVersion = common.shellCommand(
            command=util.Interpolate("echo '%(prop:got_revision)s' | tee revision.txt"),
            name="Stamping the build")

        updateBuild = common.copyAWS(
            pathFrom="revision.txt",
            pathTo="s3://{{ s3_public_bucket }}/builds/%(prop:branch_pretty)s/latest.txt",
            name="Update latest build marker in S3")

        updateCrowdin = common.shellCommand(
            command=util.Interpolate("echo api_key: '%(secret:crowdin.key)s' >> .crowdin.yaml; echo crowdin --config .crowdin.yaml upload sources -b %(prop:branch)s"),
            doStepIf={{ push_crowdin }},
            hideStepIf={{ not push_crowdin }},
            name="Update Crowdin translation keys")

        buildFoundAt = steps.SetProperty(
            property="build_found_at",
            value=util.Interpolate("s3://{{ s3_public_bucket }}/builds/{{ builds_fragment }}/"),
            name="Set S3 location for binary fetch")


        f_build = self._getBasePipeline()
        f_build.addStep(common.getWorkerPrep())
{% if deploy_snapshots %}
        f_build.addStep(common.loadMavenSettings())
        f_build.addStep(common.getBuild(override=['deploy', '-T 1C', '-Pnone', '-s', 'settings.xml']))
{% else %}
        f_build.addStep(common.getBuild())
{% endif %}
        f_build.addStep(self.getBuildSize)
        f_build.addStep(common.unloadMavenSettings())
        f_build.addStep(common.getTarballs())
        f_build.addStep(self.getBuildSize)
        f_build.addStep(stampVersion)
        f_build.addStep(self.uploadTarballs)
        f_build.addStep(buildFoundAt)
        f_build.addStep(updateBuild)
        f_build.addStep(updateCrowdin)
        f_build.addStep(common.getClean())

        return f_build


    def getBuilders(self):

        builders = []
        branch_lock = util.MasterLock(self.pretty_branch_name + "mvn_lock")

        for jdk in self.jdks:
            jdk_props = dict(self.props)
            jdk_props['jdk'] = str(jdk)

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Pull Request Build JDK " + str(jdk),
                factory=self.getPullRequestPipeline(),
                workernames=self.props['workernames'],
                collapseRequests=True,
                properties=jdk_props))

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Build JDK " + str(jdk),
                factory=self.getBuildPipeline(),
                workernames=self.props['workernames'],
                properties=jdk_props,
                collapseRequests=True,
                locks=[branch_lock.access('exclusive')]))
        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }Build"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Build",
            change_filter=util.ChangeFilter(category=None, branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Build JDK " + str(jdk) for jdk in self.jdks ])

        #PR builds
        scheds[f"{ self.pretty_branch_name }BuildPR"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Pull Requests",
            change_filter=util.ChangeFilter(category="pull", branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Pull Request Build JDK " + str(jdk) for jdk in self.jdks ])

        scheds[f"{ self.pretty_branch_name}BuildForce"] = common.getForceScheduler(
            props=self.props,
            build_type="Build",
            builderNames=[ self.pretty_branch_name + " Build JDK " + str(jdk) for jdk in self.jdks ])

        return scheds
