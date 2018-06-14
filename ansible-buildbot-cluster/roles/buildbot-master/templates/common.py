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
                util.Interpolate(os.path.normpath("{{ deployed_reports }}")),
                util.Interpolate(os.path.normpath("{{ deployed_markdown }}")),
                util.Interpolate(os.path.normpath("{{ deployed_javadocs }}")),
                util.Interpolate(os.path.normpath("{{ deployed_coverage }}")),
                util.Interpolate(os.path.normpath("{{ deployed_debs }}")),
                util.Interpolate(os.path.normpath("{{ deployed_rpms }}")),
                util.Interpolate(os.path.normpath("{{ deployed_builds_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_reports_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_markdown_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_javadocs_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_coverage_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_debs_symlink_base }}")),
                util.Interpolate(os.path.normpath("{{ deployed_rpms_symlink_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

def getPermissionsFix():
    return steps.MasterShellCommand(
        command=["chown", "-R", "{{ getent_passwd['buildbot'][1] }}:{{ getent_passwd['buildbot'][2] }}",
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
