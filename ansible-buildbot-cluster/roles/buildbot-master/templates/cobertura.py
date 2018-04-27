# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *


def getBuildPipeline(branchname, branchInfo):

    cobertura = steps.ShellCommand(
        command=[
            'mvn', '-B', '-V', '-Dmaven.repo.local=./.m2',
            '-Dmaven.repo.remote=http://{{ inventory_hostname }}/nexus',
            'cobertura:cobertura'
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build Cobertura report")

    uploadCobertura = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r target/site/cobertura {{ buildbot_scp_coverage }}"),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload code coverage report to buildmaster")

    uploadPRCobertura = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r target/site/cobertura {{ buildbot_scp_PR_coverage }}"),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload code coverage report to buildmaster")

    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(
        steps.SetProperty(
            property="branch",
            value=branchInfo['branch'],
            name="Set regular branch name"))
    f_package_debs.addStep(
        steps.SetProperty(
            property="branch_pretty",
            value=branchname,
            name="Set pretty branch name"))
    f_package_debs.addStep(
        steps.SetProperty(
            property="debs_package_version",
            value=branchInfo['debsVersion'],
            name="Set Debian package version"))
    f_package_debs.addStep(debChecker)
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsUpdate)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(debsPrep)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(debsUpload)

    return f_package_debs
