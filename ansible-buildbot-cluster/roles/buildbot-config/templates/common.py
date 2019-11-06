# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util


def shellCommand(command, name, workdir="build", env={}, haltOnFailure=True, flunkOnFailure=True, warnOnFailure=True, alwaysRun=False, doStepIf=True, hideStepIf=False):
    return steps.ShellCommand(
        command=command,
        name=name,
        workdir=workdir,
        env=env,
        flunkOnFailure=flunkOnFailure,
        haltOnFailure=haltOnFailure,
        warnOnFailure=warnOnFailure,
        alwaysRun=alwaysRun,
        doStepIf=doStepIf,
        hideStepIf=hideStepIf)


def shellArg(command, logfile, haltOnFailure=True, flunkOnFailure=True, warnOnFailure=True):
    return util.ShellArg(
        command=command,
        logfile=logfile,
        flunkOnFailure=flunkOnFailure,
        haltOnFailure=haltOnFailure,
        warnOnFailure=warnOnFailure)


def shellSequence(commands, name, workdir="build", env={}, haltOnFailure=True, flunkOnFailure=True, warnOnFailure=True, alwaysRun=False, doStepIf=True, hideStepIf=False):
    return steps.ShellSequence(
        commands=commands,
        name=name,
        workdir=workdir,
        env=env,
        flunkOnFailure=flunkOnFailure,
        haltOnFailure=haltOnFailure,
        warnOnFailure=warnOnFailure,
        alwaysRun=alwaysRun,
        doStepIf=doStepIf,
        hideStepIf=hideStepIf)


def getMavenBase():
{% if skip_tests %}
    return ['mvn', '-B', '-V', '-Dmaven.repo.local=/builder/m2', '-DskipTests']
{% else %}
    return ['mvn', '-B', '-V', '-Dmaven.repo.local=/builder/m2']
{% endif %}


def getPreflightChecks():
    return shellSequence(
        commands=[
            shellArg(
                command="df /builds -m | tail -n 1 | awk '$4 <= {{ minimum_build_diskspace }} { exit 1 }'",
                logfile='freespace')
        ],
        name="Pre-flight checks")


def getClone():
    return steps.GitHub(
        repourl="{{ source_repo_url }}",
        mode='full',
        method='fresh',
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Clone/Checkout")


def getWorkerPrep(deploy=False):
    mvn = getMavenBase()
    mvn.extend(['dependency:go-offline', '-fn'])
    commandsAry=[
        shellArg(
            command=['git', 'clean', '-fdx'],
            logfile='clean'),
        shellArg(
            command=mvn,
            logfile='deps')
    ]
    if deploy:
        commandsAry.append(copyAWS(
            pathFrom="s3://private/{{ groups['master'][0] }}/mvn/settings.xml"
            pathTo="settings.xml",
            logfile="settings"))
    return shellSequence(
        commands=commandsAry,
        name="Build Prep")


def getBuild(deploy=False):
    command = getMavenBase()
    if not deploy:
      command.extend(['clean', 'install'])
    else:
      command.extend(['clean', 'deploy', '-P', 'none', '-s', 'settings.xml'])
    return shellSequence(
        commands=[
            shellArg(
                command=['sed', '-i', 's/WARN/DEBUG/',
                         'docs/log4j/log4j.properties'],
                logfile='sed'),
            shellArg(
                command=command,
                logfile='build')
        ],
        name="Build")


def copyAWS(pathFrom, pathTo, name, doStepIf=True, hideStepIf=False):
    return _AWSStep("cp", pathFrom, pathTo, name, doStepIf, hideStepIf)

def syncAWS(pathFrom, pathTo, name, doStepIf=True, hideStepIf=False):
    return _AWSStep("sync", pathFrom, pathTo, name, doStepIf, hideStepIf)

def _AWSStep(command, pathFrom, pathTo, name, doStepIf=True, hideStepIf=False):
    return shellCommand(
        command=['aws', '--endpoint-url', '{{ s3_host }}', 's3', command, util.Interpolate(pathFrom), util.Interpolate(pathTo)],
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.secret_key")
        },
        name=name,
        doStepIf=doStepIf,
        hideStepIf=hideStepIf)


def getLatestBuildRevision():
    pathFrom = "s3://public/builds/%(prop:branch_pretty)s/latest.txt"
    pathTo = "-"
    command = 'cp'
    return steps.SetPropertyFromCommand(
        command=['aws', '--endpoint-url', '{{ s3_host }}', 's3', command, util.Interpolate(pathFrom), util.Interpolate(pathTo)],
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.secret_key")
        },
        # Note: We're overwriting this value to set it to the built revision rather than whatever it defaults to
        property="got_revision",
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Get latest build version")

@util.renderer
def _getShortBuildRevision(props):
    return props.getProperty("got_revision")[:9]

def getShortBuildRevision():
    return steps.SetProperty(
        property="short_revision",
        value=_getShortBuildRevision,
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Get build tarball short revision")

def loadSigningKey():
    pathFrom = "s3://private/{{ groups['master'][0] }}/key/signing.key"
    pathTo = "-"
    command = 'cp'
    return shellCommand(
        command=util.Interpolate("aws --endpoint-url {{ s3_host }} s3 " + command + " " + pathFrom + " " + pathTo + " | gpg --import"),
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.secret_key")
        },
        name="Load signing key")

def unloadSigningKey():
    return shellCommand(
        command=['rm', '-rf', '/builder/.gnupg'],
        alwaysRun=True,
        name="Key cleanup")


def getClean():
    return shellSequence(
        commands=[
            shellArg(
                command=['git', 'clean', '-fdx'],
                logfile='git')
        ],
        alwaysRun=True,
        name="Cleanup")
