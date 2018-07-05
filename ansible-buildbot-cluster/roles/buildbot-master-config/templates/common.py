# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *


def getMavenBase():
    return ['mvn', '-B', '-V', '-Dmaven.repo.local=/builder/m2']

def getClone():
    return steps.GitHub(
        repourl="{{ source_repo_url }}",
        mode='incremental',
        method='fresh',
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Clone/Checkout")

def getWorkerPrep():
    command = getMavenBase()
    command.extend(['dependency:go-offline', '-fn'])
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='clean'),
            util.ShellArg(
                command=command,
                logfile='deps')
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build Prep")

def getBuild():
    command = getMavenBase()
    command.extend(['clean', 'install'])
    return steps.ShellCommand(
        command=command,
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build")

def getPermissionsFix():
    return steps.MasterShellCommand(
        command=["chown", "-R", "{{ buildbot_user }}:{{ buildbot_user }}",
            util.Interpolate(os.path.normpath("{{ deployed_builds }}"))
        ],
        name="Fixing directory permissions on buildmaster")

def getClean():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='git'),
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Cleanup")
