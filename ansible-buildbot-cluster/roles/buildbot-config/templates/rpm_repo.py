# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def getBuildPipeline():

    repo_prep = steps.ShellCommand(
        command=[
            'mkdir', '-p', util.Interpolate('%(prop:rpm_repo_fragment)s/unstable/el/7/noarch/%(prop:pkg_major_version)s/')
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Prep repository structure')

    repo_fetch = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r {{ buildbot_scp_rpms_fetch }}/* %(prop:rpm_repo_fragment)s/unstable/el/7/noarch/%(prop:pkg_major_version)s/"
        ),
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Fetch packages')

    repo_build = steps.ShellCommand(
        command=[
            'createrepo', '.'
        ],
        workdir=util.Interpolate('%(prop:rpm_repo_fragment)s/unstable/el/7/noarch'),
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Build repository')

    f_rpm_repo = util.BuildFactory()
    f_rpm_repo.addStep(common.getPreflightChecks())
    f_rpm_repo.addStep(repo_prep)
    f_rpm_repo.addStep(repo_fetch)
    f_rpm_repo.addStep(common.loadSigningKey())
    f_rpm_repo.addStep(repo_build)
    f_rpm_repo.addStep(common.unloadSigningKey())

    return f_rpm_repo
