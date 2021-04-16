# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
import common


def __getBasePipeline():

    checkSpaces = common.shellSequence(
        commands=[
            common.shellArg(
                command=util.Interpolate(
                    "(! grep -rnP '\t' modules assemblies pom.xml etc --include=pom.xml)"),
                haltOnFailure=False,
                logfile='Tab Check'),
            common.shellArg(
                command=util.Interpolate(
                    "(! grep -rn ' $' modules assemblies pom.xml etc --include=pom.xml)"
                ),
                haltOnFailure=False,
                logfile='End Of Line Space Check')
        ],
        workdir="build/docs/guides",
        name="Formatting checks")

    reports = [
        'cobertura:cobertura', 'site', 'site:stage',
        '-Daggregate=true',
        '-Dcheckstyle.skip=true',
        '-P "none,!frontend"'
    ]
    site = common.getBuild(override=reports, name="Build site report")

    f_build = util.BuildFactory()
    f_build.addStep(common.getPreflightChecks())
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.setTimezone())
    f_build.addStep(common.setLocale())
    f_build.addStep(common.getBuild())
    f_build.addStep(checkSpaces)
    f_build.addStep(site)

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build


def getBuildPipeline():

    compressSite = common.compressDir(
        dirToCompress="target/staging",
        outputFile="target/site.tar.bz2")

    compressCoverage = common.compressDir(
        dirToCompress="target/site/cobertura",
        outputFile="target/coverage.tar.bz2")

    uploadSite = common.copyAWS(
        pathFrom="target/site.tar.bz2",
        pathTo="s3://public/builds/{{ reports_fragment }}",
        name="Upload site report to S3")

    uploadCoverage = common.copyAWS(
        pathFrom="target/coverage.tar.bz2",
        pathTo="s3://public/builds/{{ coverage_fragment }}",
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

    f_build = __getBasePipeline()
    f_build.addStep(compressSite)
    f_build.addStep(compressCoverage)
    f_build.addStep(uploadSite)
    f_build.addStep(uploadCoverage)
    #f_build.addStep(updateSite)
    f_build.addStep(common.getClean())

    return f_build
