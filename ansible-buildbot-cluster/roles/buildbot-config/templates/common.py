# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *


def getMavenBase():
{% if skip_tests %}
    return ['mvn', '-B', '-V', '-Dmaven.repo.local=/builder/m2', '-DskipTests']
{% else %}
    return ['mvn', '-B', '-V', '-Dmaven.repo.local=/builder/m2']
{% endif %}

def getPreflightChecks():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command="df /builds -m | tail -n 1 | awk '$4 <= {{ minimum_build_diskspace }} { exit 1 }'", logfile='freespace'),
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Pre-flight checks")

def getClone():
    return steps.GitHub(
        repourl="{{ source_repo_url }}",
        mode='full',
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
    return steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['sed','-i','s/WARN/DEBUG/','docs/log4j/log4j.properties'],
                logfile='sed'),
            util.ShellArg(
                command=command,
                logfile='build')
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build")

def loadSigningKey():
    return steps.ShellCommand(
        command="scp {{ buildbot_scp_signing_key }} /dev/stdout | gpg --import",
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Load signing key")

def unloadSigningKey():
    return steps.ShellCommand(
        command=['rm', '-rf', '/builder/.gnupg'],
        flunkOnFailure=True,
        alwaysRun=True,
        name="Key cleanup")

def getClean():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='git'),
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        alwaysRun=True,
        name="Cleanup")
