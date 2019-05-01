# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def getBuildPipeline():

    repo_prep = steps.ShellCommand(
        command=[
            'mkdir', '-p', util.Interpolate('{{ rpm_repo_fragment }}/%(prop:pkg_major_version)s/')
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Prep repository structure')

    repo_fetch = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r {{ buildbot_scp_rpms }}/* {{ rpm_repo_fragment }}/%(prop:pkg_major_version)s/"
        ),
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Fetch packages')

    repo_build = steps.ShellCommand(
        command=[
            'createrepo', '.'
        ],
        workdir=util.Interpolate('{{ rpm_repo_fragment }}'),
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Build repository')

    f_rpm_repo = util.BuildFactory()
    f_rpm_repo.addStep(common.getPreflightChecks())
    f_rpm_repo.addStep(repo_prep)
    f_rpm_repo.addStep(repo_fetch)
    f_rpm_repo.addStep(common.loadSigningKey())
    f_rpm_repo.addStep(repo_build)

    return f_rpm_repo
