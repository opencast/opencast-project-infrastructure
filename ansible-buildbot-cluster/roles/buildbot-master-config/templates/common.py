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

def getPermissionsFix():
    return steps.MasterShellCommand(
        command=["chown", "-R", "{{ buildbot_uid['ansible_facts']['getent_passwd']['buildbot'][1] }}:{{ buildbot_gid['ansible_facts']['getent_group']['buildbot'][1] }}",
            util.Interpolate(os.path.normpath("{{ build_base }}"))
        ],
        flunkOnFailure=True,
        name="Fixing directory permissions on buildmaster")

def loadSigningKey():
    return steps.ShellCommand(
        command=[
            "gpg", "--import", "{{ buildbot_config }}/signing.key"
        ],
        env={
            "GNUPGHOME": "/builder/gnupg"
        },
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Load signing key")

def getClean():
    return steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='git'),
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        alwaysRun=True,
        name="Cleanup")
