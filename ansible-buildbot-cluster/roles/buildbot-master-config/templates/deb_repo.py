# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def getBuildPipeline():

    repo_prep = steps.ShellCommand(
        command=[
            'mkdir', '-p', '{{ deb_repo_fragment }}/mini-dinstall/incoming'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Prep repository structure')

    repo_clean = steps.ShellCommand(
        command=util.Interpolate(
            'rm -f {{ deb_repo_fragment }}/mini-dinstall/incoming/opencast-%(prop:pkg_major_version)s* {{ deb_repo_fragment }}/mini-dinstall/REJECT/opencast-%(prop:pkg_major_version)s*'
        ),
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Clean repository stucture')

    repo_fetch = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r {{ buildbot_scp_debs }}/* {{ deb_repo_fragment }}/mini-dinstall/incoming"
        ),
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Fetch packages')

    #this file needs to be in the cwd for it to be picked up with mini-dinstall
    repo_copy = steps.ShellCommand(
        command=[
            'cp', '{{ buildbot_config }}/mini-dinstall.conf', '.'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Copying config file')

    repo_build = steps.ShellCommand(
        command=[
            'mini-dinstall', '-vbc', 'mini-dinstall.conf'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        name='Build repository')

    f_deb_repo = util.BuildFactory()
    f_deb_repo.addStep(common.getPreflightChecks())
    f_deb_repo.addStep(repo_prep)
    f_deb_repo.addStep(repo_clean)
    f_deb_repo.addStep(repo_fetch)
    f_deb_repo.addStep(repo_copy)
    f_deb_repo.addStep(common.loadSigningKey())
    f_deb_repo.addStep(repo_build)

    return f_deb_repo
