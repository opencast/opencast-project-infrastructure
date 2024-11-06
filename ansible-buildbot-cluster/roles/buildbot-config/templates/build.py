# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
from buildbot.process.results import SUCCESS
#from github import Github
import common

class GenerateGithubRelease(steps.BuildStep):

    def __init__(self, release_tag, release_name, release_message, **kwargs):
        super().__init__(**kwargs)

        self.tag = release_tag
        self.name = release_name
        self.message = release_message

    def run(self):
        g = Github("{{ github_token }}")

        opencast = g.get_repo("{{ source_pr_owner }}/{{ source_pr_repo }}")

        release = opencast.create_git_release(tag=f"{self.tag}", name=f"{self.name}", message=f"{self.message}", prerelease=True)
        #release.upload_asset(path="./test.txt", content_type="application/txt")
        return SUCCESS

    def getCurrentSummary(self):
        return dict({
                 "step": f"Creating { self.tag } release named { self.name }"
               })

    def getResultSummary(self):
        return dict({
                 "step": f"Created { self.tag } release named { self.name }",
                 "build": f"I dunno lol"
               })


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
            if key in props and type(props[key]) in [str, list]:
                self.props[key] = props[key]

        self.props['signing_key_filename'] = "{{ signing_key_filename }}"

        self.pretty_branch_name = self.props["branch_pretty"]
        self.jdks = self.props["jdk"]
        build_triggers = [ "assemblies", "modules", "pom.xml" ]
        self.buildFilter = lambda change: any(map(lambda filename: [ substr in filename for substr in build_triggers ], change.files))

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


    def _addBuildSteps(self, f_build, override=None, timeout=240):

        bs2 = common.getBuild(name="Build attempt 2", override=override, haltOnFailure=True, doStepIf=lambda build: build.build.results != SUCCESS, timeout=timeout)
        #NoneType object has no attribute 'results' -> going to guess bs2 isn't visible
        #bs3 = common.getBuild(name="Build attempt 3", override=override, haltOnFailure=False, doStepIf=lambda build: build.build.results != SUCCESS and bs2.build.results != SUCCESS, timeout=timeout)

        f_build.addStep(common.getBuild(override=override, haltOnFailure=False, timeout=timeout))
        f_build.addStep(bs2)
        #f_build.addStep(bs3)


    def getPullRequestPipeline(self):

        f_build = self._getBasePipeline()
        f_build.addStep(common.getWorkerPrep())
        f_build.addStep(common.getBuildPrep())
        self._addBuildSteps(f_build)
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
        override = None
{% if deploy_snapshots %}
        f_build.addStep(common.loadMavenSettings())
        f_build.addStep(common.loadSigningKey())
        override=['deploy', '-T 1C', '-Pnone', '-s', 'settings.xml'],
{% endif %}
        f_build.addStep(common.getBuildPrep())
        self._addBuildSteps(f_build, override)
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

    def getReleasePipeline(self):

        #github_release = GenerateGithubRelease(
        #    release_tag=util.Interpolate("%(prop:branch)s"),
        #    release_name=util.Interpolate("Opencast %(prop:branch)s"),
        #    release_message=util.Interpolate("Changelog available at #TODO"),
        #    haltOnFailure=True,
        #    flunkOnFailure=True)

        f_build = self._getBasePipeline()
        f_build.addStep(common.getWorkerPrep())
        f_build.addStep(common.loadMavenSettings())
        f_build.addStep(common.loadSigningKey())
        f_build.addStep(common.getBuildPrep())
        override=['install', 'nexus-staging:deploy', 'nexus-staging:release', '-P', 'release,none', '-s', 'settings.xml', '-DstagingProgressTimeoutMinutes=10']
        self._addBuildSteps(f_build, override=override, timeout=1200)
        f_build.addStep(common.unloadSigningKey())
        f_build.addStep(common.unloadMavenSettings())
        #f_build.addStep(common.getTarballs())
        #f_build.addStep(github_release)
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

{% if deploy_tags | default(false) %}
        if "develop" != self.props['git_branch_name']:
            jdk_props = dict(self.props)
            #We use the oldest JDK for release builds
            jdk_props['jdk'] = str(self.jdks[0])

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Release",
                factory=self.getReleasePipeline(),
                workernames=self.props['workernames'],
                properties=jdk_props,
                collapseRequests=True,
                locks=[branch_lock.access('exclusive')]))
{% endif %}

        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }Build"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Build",
            change_filter=util.ChangeFilter(repository=["https://code.loganite.ca/opencast/opencast.git", "git@code.loganite.ca:opencast/opencast.git"], category='push', branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Build JDK " + str(jdk) for jdk in self.jdks ])

        #PR builds
        scheds[f"{ self.pretty_branch_name }BuildPR"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Pull Requests",
            change_filter=util.ChangeFilter(repository=["https://code.loganite.ca/opencast/opencast.git", "git@code.loganite.ca:opencast/opencast.git"], category=["pull", "merge_request"], branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Pull Request Build JDK " + str(jdk) for jdk in self.jdks ])

        scheds[f"{ self.pretty_branch_name}BuildForce"] = common.getForceScheduler(
            name=self.pretty_branch_name + "Build",
            props=self.props,
            builderNames=[ self.pretty_branch_name + " Build JDK " + str(jdk) for jdk in self.jdks ])

{% if deploy_tags | default(false) %}
        if "develop" != self.props['git_branch_name']:
            #Set the jdk to use at the scheduler level.  We want the oldest jdk supported by a branch.
            jdkprops = dict(self.props)
            jdkprops['jdk'] = sorted(self.jdks)[0]

            #Regular releases
            scheds[f"{ self.pretty_branch_name }Release"] = common.getAnyBranchScheduler(
                name=self.pretty_branch_name + " Release",
                properties=jdkprops,
                #This regex is looking for something like 11.1, so we use the major package version and a static ".*"
                change_filter=util.ChangeFilter(repository="https://code.loganite.ca/opencast/opencast.git", category='tag_push', branch_re=self.props['pkg_major_version'] + ".*", repository_re=".*opencast.git"),
                builderNames=[ self.pretty_branch_name + " Release"])

            codebase = [
                util.CodebaseParameter(
                    "",
                    label="Build Settings",
                    # will generate a combo box
                    branch=util.StringParameter(
                        label="Release Version",
                        name="branch",
                        default=self.pretty_branch_name,
                    ),
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

            scheds[f"{ self.pretty_branch_name}ReleaseForce"] = common.getForceScheduler(
                name=self.pretty_branch_name + "Release",
                props=jdkprops,
                codebase=codebase,
                builderNames=[ self.pretty_branch_name + " Release"])
{% endif %}

        return scheds
