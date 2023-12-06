# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
from buildbot.process.results import SUCCESS
import common

class Reports():

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

    def __init__(self, props):
        for key in Reports.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Reports.OPTIONAL_PARAMS:
            if key in props and type(props[key]) in [str, list]:
                self.props[key]

        self.props['cores'] = "1" #cores # Fixed at 1 since the reports aren't multithreaded
        self.pretty_branch_name = self.props["branch_pretty"]
        self.jdks = self.props["jdk"]
        build_triggers = [ "assemblies", "modules", "pom.xml" ]
        self.buildFilter = lambda change: any(map(lambda filename: [ substr in filename for substr in build_triggers ], change.files))

    def __getBasePipeline(self):

        checkSpaces = common.shellSequence(
            commands=[
                common.shellArg(
                    command=util.Interpolate(
                        "(! grep -rnP '\t' modules assemblies pom.xml etc --include=pom.xml)"),
                    haltOnFailure=False,
                    logname='Tab Check'),
                common.shellArg(
                    command=util.Interpolate(
                        "(! grep -rn ' $' modules assemblies pom.xml etc --include=pom.xml)"
                    ),
                    haltOnFailure=False,
                    logname='End Of Line Space Check')
            ],
            workdir="build/docs/guides",
            name="Formatting checks")

        reports = [
            'site', 'site:stage',
            '-Daggregate=true',
            '-Dcheckstyle.skip=true',
            '-P', 'none,!frontend'
        ]
        site = common.getBuild(override=reports, name="Build site report", haltOnFailure=False)
        site2 = common.getBuild(override=reports, name="Build site report attempt 2", haltOnFailure=False, doStepIf=lambda build: build.build.results != SUCCESS)
        site3 = common.getBuild(override=reports, name="Build site report attempt 3", doStepIf=lambda build: build.build.results != SUCCESS)

        f_build = util.BuildFactory()
        f_build.addStep(common.getPreflightChecks())
        f_build.addStep(common.getClone())
        f_build.addStep(common.getWorkerPrep())
        f_build.addStep(common.setTimezone())
        f_build.addStep(common.setLocale())
        f_build.addStep(common.getBuildPrep())
        f_build.addStep(common.getBuild(haltOnFailure=False))
        f_build.addStep(common.getBuild(name="Build attempt 2", haltOnFailure=False, doStepIf=lambda build: build.build.results != SUCCESS))
        f_build.addStep(common.getBuild(name="Build attempt 3", doStepIf=lambda build: build.build.results != SUCCESS))
        f_build.addStep(checkSpaces)
        f_build.addStep(site)
        f_build.addStep(site2)
        f_build.addStep(site3)

        return f_build


    def getPullRequestPipeline(self):

        f_build = self.__getBasePipeline()
        f_build.addStep(common.getClean())

        return f_build


    def getBuildPipeline(self):

        compressSite = common.compressDir(
            dirToCompress="target/staging",
            outputFile="target/site.tar.bz2")

        compressCoverage = common.compressDir(
            dirToCompress="target/site/cobertura",
            outputFile="target/coverage.tar.bz2")

        uploadSite = common.copyAWS(
            pathFrom="target/site.tar.bz2",
            pathTo="s3://{{ s3_public_bucket }}/builds/{{ reports_fragment }}",
            name="Upload site report to S3")

        uploadCoverage = common.copyAWS(
            pathFrom="target/coverage.tar.bz2",
            pathTo="s3://{{ s3_public_bucket }}/builds/{{ coverage_fragment }}",
            name="Upload coverage report to S3")

        updateSite = steps.MasterShellCommand(
            command=util.Interpolate(
                "ln -s {{ deployed_reports }}/apidocs {{ deployed_javadocs }} && \
                ln -s {{ deployed_reports }}/cobertura {{ deployed_coverage }} && \
                rm -f {{ deployed_reports_symlink }} {{ deployed_javadocs_symlink }} {{ deployed_coverage_symlink }} && \
                ln -s {{ deployed_reports }} {{ deployed_reports_symlink }} && \
                ln -s {{ deployed_javadocs }} {{ deployed_javadocs_symlink }} && \
                ln -s {{ deployed_coverage }} {{ deployed_coverage_symlink }}"
            ),
            flunkOnFailure=True,
            name="Deploy Reports")

        f_build = self.__getBasePipeline()
        f_build.addStep(compressSite)
        f_build.addStep(compressCoverage)
        f_build.addStep(uploadSite)
        f_build.addStep(uploadCoverage)
        #f_build.addStep(updateSite)
        f_build.addStep(common.getClean())

        return f_build


    def getBuilders(self):

        builders = []
        branch_lock = util.MasterLock(self.pretty_branch_name + "mvn_report lock")

        for jdk in self.jdks:
            jdk_props = dict(self.props)
            jdk_props['jdk'] = str(jdk)

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Pull Request Reports JDK " + str(jdk),
                factory=self.getPullRequestPipeline(),
                workernames=self.props['workernames'],
                collapseRequests=True,
                properties=jdk_props))

            builders.append(util.BuilderConfig(
                name=self.pretty_branch_name + " Reports JDK " + str(jdk),
                factory=self.getBuildPipeline(),
                workernames=self.props['workernames'],
                properties=jdk_props,
                collapseRequests=True,
                locks=[branch_lock.access('exclusive')]))
        return builders


    def getSchedulers(self):

        scheds = {}

        #Regular builds
        scheds[f"{ self.pretty_branch_name }Reports"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Reports",
            change_filter=util.ChangeFilter(category=None, branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Reports JDK " + str(jdk) for jdk in self.jdks ])

        #PR builds
        scheds[f"{ self.pretty_branch_name }ReportsPR"] = common.getAnyBranchScheduler(
            name=self.pretty_branch_name + " Pull Request Reports",
            change_filter=util.ChangeFilter(category="pull", branch_re=self.props['git_branch_name']),
            fileIsImportant=self.buildFilter,
            builderNames=[ self.pretty_branch_name + " Pull Request Reports JDK " + str(jdk) for jdk in self.jdks ])

        scheds[f"{ self.pretty_branch_name}ReportsForce"] = common.getForceScheduler(
            props=self.props,
            build_type="Report",
            builderNames=[ self.pretty_branch_name + " Reports JDK " + str(jdk) for jdk in self.jdks ])

        return scheds
