# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers
import random


def getAnyBranchScheduler(name, builderNames, fileIsImportant=lambda fn: True, change_filter=None, properties=dict()):
    return schedulers.AnyBranchScheduler(
        name=name,
        # NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        treeStableTimer={{ stability_limit }},
        builderNames=builderNames,
        properties=properties,
        change_filter=change_filter,
        fileIsImportant=fileIsImportant)


def getForceScheduler(props, build_type, builderNames):
    pretty_branch_name = props['branch_pretty']

    forceParams = [
        util.CodebaseParameter(
            "",
            label="Main repository",
            # will generate a combo box
            branch=util.FixedParameter(
                name="branch",
                default=props['git_branch_name'],
            ),
            # will generate nothing in the form, but revision, repository,
            # and project are needed by buildbot scheduling system so we
            # need to pass a value ("")
            revision=util.FixedParameter(name="revision", default="HEAD"),
            repository=util.FixedParameter(
                name="repository", default="{{ source_repo_url }}"),
            project=util.FixedParameter(name="project", default=""),
        ),
    ]

# Note: This is a hack, but we need a unique name for the force schedulers, and it can't have special characters in it, and it can't be longer than a certain length
    return schedulers.ForceScheduler(
        name=f"F{ pretty_branch_name[0:2] }{ build_type }".replace(".", "x").replace(" ", ""),
        buttonName="Force Build",
        label="Force Build Settings",
        builderNames=builderNames,
        codebases=forceParams,

        # will generate a text input
        reason=util.StringParameter(
            name="reason",
            label="Reason:",
            required=False,
            size=80,
            default=""),

        # in case you don't require authentication this will display
        # input for user to type his name
        username=util.UserNameParameter(label="your name:", size=80))


def shellCommand(command, name, workdir="build", env={}, haltOnFailure=True, flunkOnFailure=True, warnOnFailure=True, alwaysRun=False, doStepIf=True, hideStepIf=False, locks=[]):
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
        hideStepIf=hideStepIf,
        locks=locks)


def shellArg(command, logname, haltOnFailure=True, flunkOnFailure=True, warnOnFailure=True):
    return util.ShellArg(
        command=command,
        logname=logname,
        flunkOnFailure=flunkOnFailure,
        haltOnFailure=haltOnFailure,
        warnOnFailure=warnOnFailure)


def shellSequence(commands, name, workdir="build", env={}, haltOnFailure=True, flunkOnFailure=True, warnOnFailure=True, alwaysRun=False, doStepIf=True, hideStepIf=False, timeout=240, locks=[]):
    return steps.ShellSequence(
        commands=commands,
        name=name,
        workdir=workdir,
        env=env,
        timeout=timeout,
        flunkOnFailure=flunkOnFailure,
        haltOnFailure=haltOnFailure,
        warnOnFailure=warnOnFailure,
        alwaysRun=alwaysRun,
        doStepIf=doStepIf,
        hideStepIf=hideStepIf,
        locks=locks)



def getPreflightChecks():
    return shellSequence(
        commands=[
            shellArg(
                command="df /builds -m | tail -n 1 | awk '$4 <= {{ minimum_build_diskspace }} { exit 1 }'",
                logname='freespace')
        ],
        name="Pre-flight checks")


def getClone(name="Clone/Checkout", url="{{ source_repo_url }}", branch=None):
    args = {
        "repourl": url,
        "mode": 'full',
        "method": 'fresh',
        "haltOnFailure": True,
        "flunkOnFailure": True,
        "name": name
    }
    if None != branch:
        args["branch"] = branch
        args["alwaysUseLatest"] = True
        return steps.Git(**args)
    if "github" in url:
        return steps.GitLab(**args)
    elif "gitlab" in url:
        return steps.GitLab(**args)
    else:
        return steps.Git(**args)


def getWorkerPrep():
    commandsAry = [
        shellArg(
            command=['git', 'clean', '-fdx'],
            logname='clean'),
    ]
    return shellSequence(
        commands=commandsAry,
        name="Build Prep")


@util.renderer
def getMavenEnv(props):
    jdk = props.getProperty("jdk")
    image = props.getProperty("image")
    if "deb" in image or "ubu" in image:
        java_home = "/usr/lib/jvm/java-" + str(jdk) + "-openjdk-amd64"
    elif "cent" in image:
        if int(jdk) > 8:
            java_home = "/usr/lib/jvm/java-" + str(jdk) + "-openjdk"
        else:
            java_home = "/usr/lib/jvm/java-1." + str(jdk) + ".0-openjdk"
    env={
        "LANG": util.Interpolate("%(prop:LANG)s"),
        "LC_ALL": util.Interpolate("%(prop:LANG)s"),
        "LANGUAGE": util.Interpolate("%(prop:LANG)s"),
        "TZ": util.Interpolate("%(prop:TZ)s"),
        "JAVA_HOME": java_home,
        "PATH": [ java_home + "/bin", "${PATH}" ],
        "CI": "true"
    }
    return env


def getBuild(override=None, name="Build", workdir="build", timeout=240):
    command = ['mvn', '-B', '-V', '-Dmaven.repo.local=/builder/m2', '-Dsurefire.rerunFailingTestsCount=2']
{% if skip_tests %}
    command.append('-DskipTests')
{% endif %}
    if not override:
        command.extend(['install', '-T', util.Interpolate('%(prop:cores)s'), '-Pnone'])
    else:
        command.extend(override)
    return shellSequence(
        commands=[
#            shellArg(
#                command=['sed', '-i', 's/WARN/DEBUG/',
#                         'docs/log4j/log4j.properties'],
#                logname='log-settings',
#                haltOnFailure=False,
#                flunkOnFailure=False,
#                warnOnFailure=False),
            shellArg(
                #This needs to be pkg_major_version so that it's numeric
                command=['/builder/install-ffmpeg.sh', util.Property('ffmpeg', default=util.Property('pkg_major_version'))],
                logname='ffmpeg',
                haltOnFailure=True),
            shellArg(
                command=['sed', '-i', 's/captureTimeout: [0-9]*/captureTimeout: 120000/',
                         'modules/admin-ui/src/test/resources/karma.conf.js'],
                logname='old-timeout',
                haltOnFailure=False,
                flunkOnFailure=False,
                warnOnFailure=False),
            shellArg(
                command=['sed', '-i', 's/captureTimeout: [0-9]*/captureTimeout: 120000/',
                         'modules/admin-ui-frontend/test/karma.conf.js'],
                logname='new-timeout',
                haltOnFailure=False,
                flunkOnFailure=False,
                warnOnFailure=False),
            shellArg(
                command=command,
                logname='build')
        ],
        env=getMavenEnv,
        workdir=workdir,
        name=name,
        timeout=timeout)

def getTarballs():
    return getBuild(
        override=['install', '-T 1C', '-P', 'dist'],
        workdir="build/assemblies",
        name="Building the tarballs")


def compressDir(dirToCompress, outputFile, workdir="build"):
    return shellCommand(
         command=['tar', 'cjf', outputFile, dirToCompress],
         workdir=workdir,
         name=f"Compressing { dirToCompress }")


def copyAWS(pathFrom, pathTo, name, doStepIf=True, hideStepIf=False):
    return AWSStep(
        ['s3', 'cp', util.Interpolate(pathFrom), util.Interpolate(pathTo)],
        name, doStepIf, hideStepIf)


def syncAWS(pathFrom, pathTo, name, doStepIf=True, hideStepIf=False):
    return AWSStep(
        ['s3', 'sync', util.Interpolate(pathFrom), util.Interpolate(pathTo)],
        name, doStepIf, hideStepIf)


def AWSStep(command, name, doStepIf=True, hideStepIf=False, access=util.Secret("s3.public_access_key"), secret=util.Secret("s3.public_secret_key")):
    commandAry = list()
    commandAry.extend(['aws', '--endpoint-url', '{{ s3_host }}']),
    if type(command) == list:
        commandAry.extend(command)
    else:
        commandAry.append(command)
    return shellCommand(
        command=commandAry,
        env={
            "AWS_ACCESS_KEY_ID": access,
            "AWS_SECRET_ACCESS_KEY": secret
        },
        name=name,
        doStepIf=doStepIf,
        hideStepIf=hideStepIf)


def deployS3fsSecrets():
    return shellCommand(
        command=util.Interpolate("echo '%(secret:s3.public_access_key)s:%(secret:s3.public_secret_key)s' > /builder/.passwd-s3fs && chmod 600 /builder/.passwd-s3fs"),
        name="Deploying S3 auth details")

def mountS3fs():
    return shellCommand(
        command=util.Interpolate(" ".join(
            ["mkdir", "-p", "/builder/s3", "&&",
             "s3fs",
             "-o", "use_path_request_style",
             "-o", "url={{ s3_host }}/",
             "-o", "uid=%(prop:builder_uid)s,gid=%(prop:builder_gid)s,umask=0000",
             "{{ s3_public_bucket }}", "/builder/s3"])),
        name="Mounting S3")

def unmountS3fs():
    return shellCommand(
        command=["fusermount", "-u", "/builder/s3"],
        name="Unmounting S3")

def cleanupS3Secrets():
    return shellCommand(
        command=["rm", "-f", ".passwd-s3fs"],
        name="Cleaning up S3 secrets")


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
        name="Fetching maven settings")


def unloadMavenSettings():
    return shellCommand(
        command=['rm', '-rfv', 'settings.xml'],
        alwaysRun=True,
        name="Settings Cleanup")


def setTimezone():
    offsetHour = random.randint(-6, 2) #random.randint(-12, 14)
    offsetMin = "00" #random.choice(["00", "15", "30", "45"]).zfill(2)
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
                command=['rm', '-rf', util.Interpolate("%(prop:builddir)s")],
                logname='rm')
        ],
        alwaysRun=True,
        name="Cleanup")
