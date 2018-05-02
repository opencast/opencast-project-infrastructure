# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *


def getClone():
    return steps.GitHub(
        repourl="{{ source_repo_url }}",
        mode='incremental',
        method='fresh',
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Clone/Checkout")

def getWorkerPrep():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='clean'),
            util.ShellArg(
                command=[
                    'mvn', '-B', '-V', '-Dmaven.repo.local=./.m2',
                    '-Dmaven.repo.remote=http://{{ inventory_hostname }}/nexus',
                    'dependency:go-offline', '-fn'
                ],
                logfile='deps')
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build Prep")

def getBuild():
    return steps.ShellCommand(
        command=[
            'mvn', '-B', '-V', '-Dmaven.repo.local=./.m2',
            '-Dmaven.repo.remote=http://{{ inventory_hostname }}/nexus',
            'clean', 'install'
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build")

def getMasterPrep():
    return steps.MasterShellCommand(
        command=[
            util.Interpolate('mkdir -p ' +
                os.path.normpath("{{ artifacts_dist_base }} ") +
                os.path.normpath("{{ artifacts_dist_base }}/reports ") +
                os.path.normpath("{{ artifacts_dist_base }}/debs ") +
                os.path.normpath("{{ artifacts_dist_base }}/rpms ") +
                os.path.normpath("{{ deployed_reports_symlink_base }} " +
                " && chown -R {{ getent_passwd['buildbot'][1] }}:{{ getent_passwd['buildbot'][2] }} " +
                os.path.normpath("{{ artifacts_dist_base }}")
                )
            )
        ],
        name="Prep relevant directories on buildmaster")

def getClean():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='git'),
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Cleanup")
