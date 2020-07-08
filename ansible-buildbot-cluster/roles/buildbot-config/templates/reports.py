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

    command = common.getMavenBase()
    command.extend([
        'cobertura:cobertura', 'site', 'site:stage',
        '-Daggregate=true',
        '-Dcheckstyle.skip=true',
        '-P "none,!frontend"'
    ])
    #Building reports with JDK 8
    env=common.getJDKSetting(8)
    site = common.shellCommand(
        command=command,
        env=env,
        name="Build site report")

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

    uploadSite = common.syncAWS(
        pathFrom="target/staging",
        pathTo="s3://public/builds/{{ reports_fragment }}",
        name="Upload mvn site to S3")

    uploadCoverage = common.syncAWS(
        pathFrom="target/site/cobertura",
        pathTo="s3://public/builds/{{ coverage_fragment }}",
        name="Upload Cobertura report to S3")

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
    #f_build.addStep(masterPrep)
    f_build.addStep(uploadSite)
    #f_build.addStep(updateSite)
    f_build.addStep(common.getClean())

    return f_build
