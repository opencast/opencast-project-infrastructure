# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import common


def getBuildPipeline():

    site = steps.ShellCommand(
        command=[
            'mvn', '-B', '-V', '-Dmaven.repo.local=./.m2',
            '-Dmaven.repo.remote=http://{{ inventory_hostname }}/nexus',
            'site', 'site:stage',
            util.Interpolate(
                '-DstagingDirectory=/buildbot/%(prop:parent_fragment)s')
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build site report")

    uploadSite = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r /buildbot/%(prop:parent_fragment)s {{ buildbot_scp_reports }}"
        ),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload site report to buildmaster")

    updateSite = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_reports_symlink }} && ln -s {{ deployed_reports }} {{ deployed_reports_symlink }} && ln -s {{ deployed_javadocs }} {{ deployed_javadocs_symlink }}"
        ),
        name="Deploy Reports")

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.getBuild())
    f_build.addStep(site)
    f_build.addStep(common.getMasterPrep())
    f_build.addStep(common.getPermissionsFix())
    f_build.addStep(uploadSite)
    f_build.addStep(updateSite)
    f_build.addStep(common.getClean())

    return f_build
