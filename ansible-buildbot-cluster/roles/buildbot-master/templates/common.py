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

def getMasterPrep():
    return steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}")),
                util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}/reports")),
                util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}/markdown")),
                util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}/debs")),
                util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}/rpms")),
                util.Interpolate(os.path.normpath("{{ deployed_reports_symlink_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

def getPermissionsFix():
    return steps.MasterShellCommand(
        command=["chown", "-R", "{{ getent_passwd['buildbot'][1] }}:{{ getent_passwd['buildbot'][2] }}",
            util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}"))
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

def getPrettyName(pretty_branch_name):
	return steps.SetProperty(
        property="branch_pretty",
        value=pretty_branch_name,
        name="Set pretty branch name")
