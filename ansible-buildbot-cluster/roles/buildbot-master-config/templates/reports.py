# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common


def __getBasePipeline():

    checkSpaces = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=util.Interpolate(
                    "(! grep -rnP '\t' modules assemblies pom.xml etc --include=pom.xml)"),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='Tab Check'),
            util.ShellArg(
                command=util.Interpolate(
                    "(! grep -rn ' $' modules assemblies pom.xml etc --include=pom.xml)"
                ),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='End Of Line Space Check')
        ],
        workdir="build/docs/guides",
        name="Formatting checks",
        haltOnFailure=False,
        flunkOnFailure=True)

    command = common.getMavenBase()
    command.extend([
            'cobertura:cobertura', 'site', 'site:stage',
            util.Interpolate(
                '-DstagingDirectory=/builder/{{ artifacts_fragment }}')
        ])
    site = steps.ShellCommand(
        command=command,
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build site report")

    f_build = util.BuildFactory()
    f_build.addStep(common.getPreflightChecks())
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())
    f_build.addStep(checkSpaces)
    f_build.addStep(site)

    return f_build

def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline():

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_reports }}")),
                util.Interpolate(os.path.normpath("{{ deployed_reports_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_javadocs_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_coverage_symlink_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

    uploadSite = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r /builder/{{ artifacts_fragment }}/* {{ buildbot_scp_reports }}"
        ),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload site report to buildmaster")

    updateSite = steps.MasterShellCommand(
        command=util.Interpolate(
            "ln -s {{ deployed_reports }}/apidocs {{ deployed_javadocs }} && \
            ln -s {{ deployed_reports }} {{ deployed_coverage }} && \
            rm -f {{ deployed_reports_symlink }} {{ deployed_javadocs_symlink }} {{ deployed_coverage_symlink }} && \
            ln -s {{ deployed_reports }} {{ deployed_reports_symlink }} && \
            ln -s {{ deployed_javadocs }} {{ deployed_javadocs_symlink }} && \
            ln -s {{ deployed_coverage }} {{ deployed_coverage_symlink }}"
        ),
        name="Deploy Reports")

    f_build = __getBasePipeline()
    f_build.addStep(masterPrep)
    f_build.addStep(common.getPermissionsFix())
    f_build.addStep(uploadSite)
    f_build.addStep(updateSite)
    f_build.addStep(common.getClean())

    return f_build
