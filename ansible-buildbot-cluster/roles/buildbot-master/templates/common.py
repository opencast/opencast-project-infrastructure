# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *


def getClone(branchname, branchInfo):

    return steps.GitHub(
        repourl="{{ source_repo_url }}",
        mode='incremental',
        method='fresh',
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Clone/Checkout")


def getClean():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='git'),
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Cleanup")
