# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import common


def __getBasePipeline():

    command = common.getMavenBase()
    command.extend([
            'site', 'site:stage',
            util.Interpolate(
                '-DstagingDirectory=/builder/%(prop:parent_fragment)s')
        ])
    site = steps.ShellCommand(
        command=command,
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build site report")

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())
    f_build.addStep(site)

    return f_build

def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline(pretty_branch_name):


    uploadSite = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r /builder/%(prop:parent_fragment)s {{ buildbot_scp_reports }}"
        ),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload site report to buildmaster")

    updateSite = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_reports_symlink }} && ln -s {{ deployed_reports }} {{ deployed_reports_symlink }} && ln -s {{ deployed_javadocs }} {{ deployed_javadocs_symlink }}"
        ),
        name="Deploy Reports")

    f_build = __getBasePipeline()
    f_build.addStep(common.getPrettyName(pretty_branch_name))
    f_build.addStep(common.getMasterPrep())
    f_build.addStep(common.getPermissionsFix())
    f_build.addStep(uploadSite)
    f_build.addStep(updateSite)
    f_build.addStep(common.getClean())

    return f_build
