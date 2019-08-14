# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def getBuildPipeline():

    repo_prep = common.shellCommand(
        command=[
            'mkdir', '-p', util.Interpolate('%(prop:deb_repo_fragment)s/mini-dinstall/incoming')
        ],
        name='Prep repository structure')

    repo_clean = common.shellCommand(
        command=util.Interpolate(
            'rm -f %(prop:deb_repo_fragment)s/mini-dinstall/incoming/opencast-%(prop:pkg_major_version)s* {{ deb_repo_fragment }}/mini-dinstall/REJECT/opencast-%(prop:pkg_major_version)s*'
        ),
        name='Clean repository stucture')

    repo_fetch = common.shellCommand(
        command=util.Interpolate(
            "scp -r {{ buildbot_scp_debs_fetch }}/* %(prop:deb_repo_fragment)s/mini-dinstall/incoming"
        ),
        name='Fetch packages')

    #this file needs to be in the cwd for it to be picked up with mini-dinstall
    repo_copy = common.shellCommand(
        command=[
            'cp', '{{ buildbot_config }}/mini-dinstall.conf', '.'
        ],
        name='Copying config file')

    repo_build = common.shellCommand(
        command=[
            'mini-dinstall', '-vbc', 'mini-dinstall.conf'
        ],
        name='Build repository')

    f_deb_repo = util.BuildFactory()
    f_deb_repo.addStep(common.getPreflightChecks())
    f_deb_repo.addStep(repo_prep)
    f_deb_repo.addStep(repo_clean)
    f_deb_repo.addStep(repo_fetch)
    f_deb_repo.addStep(repo_copy)
    f_deb_repo.addStep(common.loadSigningKey())
    f_deb_repo.addStep(repo_build)
    f_deb_repo.addStep(common.unloadSigningKey())

    return f_deb_repo
