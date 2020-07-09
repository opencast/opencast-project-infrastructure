# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util
import random


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


def getWorkerPrep():
    commandsAry = [
        shellArg(
            command=['git', 'clean', '-fdx'],
            logfile='clean'),
    ]
    return shellSequence(
        commands=commandsAry,
        name="Build Prep")


#TODO: Generalize this and use it
def getJDKBuilds():
    return [8, 11]


@util.renderer
def getMavenEnv(props):
    jdk = props.getProperty("jdk")
    env={
        "LANG": util.Interpolate("%(prop:LANG)s"),
        "LC_ALL": util.Interpolate("%(prop:LANG)s"),
        "LANGUAGE": util.Interpolate("%(prop:LANG)s"),
        "TZ": util.Interpolate("%(prop:TZ)s"),
        "JAVA_HOME": "/usr/lib/jvm/java-1." + str(jdk) + ".0-openjdk-amd64",
        "PATH": ["/usr/lib/jvm/java-1." + str(jdk) + ".0-openjdk-amd64/bin", "${PATH}"]
    }
    return env


def getBuild(deploy=False, jdk=8):
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
        env=getMavenEnv,
        name="Build")


def copyAWS(pathFrom, pathTo, name, doStepIf=True, hideStepIf=False, access=util.Secret("s3.public_access_key"), secret=util.Secret("s3.public_secret_key")):
    return _AWSStep("cp", pathFrom, pathTo, name, doStepIf, hideStepIf, access, secret)


def syncAWS(pathFrom, pathTo, name, doStepIf=True, hideStepIf=False, access=util.Secret("s3.public_access_key"), secret=util.Secret("s3.public_secret_key")):
    return _AWSStep("sync", pathFrom, pathTo, name, doStepIf, hideStepIf, access, secret)


def _AWSStep(command, pathFrom, pathTo, name, doStepIf=True, hideStepIf=False, access=util.Secret("s3.public_access_key"), secret=util.Secret("s3.public_secret_key")):
    return shellCommand(
        command=['aws', '--endpoint-url', '{{ s3_host }}', 's3', command, util.Interpolate(pathFrom), util.Interpolate(pathTo)],
        env={
            "AWS_ACCESS_KEY_ID": access,
            "AWS_SECRET_ACCESS_KEY": secret
        },
        name=name,
        doStepIf=doStepIf,
        hideStepIf=hideStepIf)


def getLatestBuildRevision():
    pathFrom = "s3://{{ s3_public_bucket }}/builds/%(prop:branch_pretty)s/latest.txt"
    pathTo = "-"
    command = 'cp'
    return steps.SetPropertyFromCommand(
        command=['aws', '--endpoint-url', '{{ s3_host }}', 's3', command, util.Interpolate(pathFrom), util.Interpolate(pathTo)],
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.public_access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.public_secret_key")
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
    pathFrom = "s3://{{ s3_private_bucket }}/{{ groups['master'][0] }}/key/signing.key"
    pathTo = "-"
    command = 'cp'
    return shellCommand(
        command=util.Interpolate("aws --endpoint-url {{ s3_host }} s3 " + command + " " + pathFrom + " " + pathTo + " | gpg --import"),
        env={
            "AWS_ACCESS_KEY_ID": util.Secret("s3.private_access_key"),
            "AWS_SECRET_ACCESS_KEY": util.Secret("s3.private_secret_key")
        },
        name="Load signing key")


def unloadSigningKey():
    return shellCommand(
        command=['rm', '-rf', '/builder/.gnupg'],
        alwaysRun=True,
        name="Key cleanup")


def loadMavenSettings():
    return copyAWS(
        pathFrom="s3://{{ s3_private_bucket }}/{{ groups['master'][0] }}/mvn/settings.xml",
        pathTo="settings.xml",
        access=util.Secret("s3.private_access_key"),
        secret=util.Secret("s3.private_secret_key"),
        name="Fetching maven settings")


def unloadMavenSettings():
    return shellCommand(
        command=['rm', '-rfv', 'settings.xml'],
        alwaysRun=True,
        name="Settings Cleanup")


def setTimezone():
    offsetHour = random.randint(-12, 14)
    offsetMin = random.choice(["00", "15", "30", "45"]).zfill(2)
    if offsetHour >= 0:
        tz = "UTC+" + str(offsetHour).zfill(2) + ":" + offsetMin
    else:
        tz = "UTC" + str(offsetHour).zfill(2) + ":" + offsetMin
    return steps.SetProperty(
        property="TZ",
        value=tz,
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Generate timezone offset for testing")


def setLocale():
    return steps.SetProperty(
        property="LANG",
        value=random.choice(["en_US.utf8", "de_DE.utf8", "es_ES.utf8", "fr_FR.utf8"]),
        flunkOnFailure=True,
        haltOnFailure=True,
        name="Generate locale for testing")


def getClean():
    return shellSequence(
        commands=[
            shellArg(
                command=['git', 'clean', '-fdx'],
                logfile='git')
        ],
        alwaysRun=True,
        name="Cleanup")
