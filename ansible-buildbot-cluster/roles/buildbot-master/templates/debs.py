# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *

def wasCloned(step):
    if step.getProperty("alreadyCloned") == "True":
        return True
    else:
        return False


def wasNotCloned(step):
    return not wasCloned(step)


def hideIfAlreadyCloned(results, step):
    return wasCloned(step)


def hideIfNotAlreadyCloned(results, step):
    return wasNotCloned(step)


def getBuildPipeline(branchname , branchInfo):

    debChecker = steps.SetPropertyFromCommand(
        command="[ -d .git ] && echo True || echo False",
        property="alreadyCloned",
        name="Checking if this is a fresh clone")

    debsClone = steps.ShellCommand(
        command=[
            'git', 'clone', "{{ source_deb_repo_url }}", '--branch',
            util.Property('branch'), './'
        ],
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasNotCloned,
        hideStepIf=hideIfAlreadyCloned,
        name="Cloning debian packaging configs")

    debsUpdate = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['git', 'fetch'], flunkOnFailure=True,
                logfile='fetch'),
            util.ShellArg(
                command=[
                    'git', 'reset', '--hard',
                    util.Interpolate('origin/%(prop:branch)s')
                ],  #We use reset here to get rid of other entries in the changelog
                flunkOnFailure=True,
                logfile='checkout')
        ],
        workdir="build",
        flunkOnFailure=True,
        haltOnFailure=True,
        doStepIf=wasCloned,
        hideStepIf=hideIfNotAlreadyCloned,
        name="Resetting debian packaging configs")

    debsVersion = steps.SetPropertyFromCommand(
        command="git rev-parse HEAD",
        property="deb_script_rev",
        flunkOnFailure=True,
        warnOnFailure=True,
        haltOnFailure=True,
        workdir="build",
        name="Get Debian script revision")

    debsClean = steps.ShellCommand(
        command=['rm', '-rf', 'binaries', 'outputs'],
        workdir="build",
        flunkOnFailure=False,
        warnOnFailure=True,
        name="Cleaning debian packaging directories")

    debsPrep = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=[
                    'dch', '--newversion',
                    util.Interpolate(
                        '%(prop:debs_package_version)s-%(prop:parent_build)s'),
                    '-b', '-D', 'unstable', '-u', 'low', '--empty',
                    util.Interpolate(
                        'Build revision %(prop:parent_revision)s, built with %(prop:deb_script_rev)s scripts'
                    )
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='dch'),
            util.ShellArg(
                command=[
                    'git', 'config', 'user.email', 'buildbot@opencast.org'
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='email'),
            util.ShellArg(
                command=['git', 'config', 'user.name', 'Buildbot'],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='authorname'),
            util.ShellArg(
                command=[
                    'git', 'commit', '-am', 'Automated commit prior to build'
                ],
                flunkOnFailure=True,
                warnOnFailure=True,
                logfile='commit')
        ],
        workdir="build/opencast",
        name="Prepping Debs",
        haltOnFailure=True,
        flunkOnFailure=True)

    debsFetch = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=[
                    'mkdir', '-p',
                    util.Interpolate('binaries/%(prop:debs_package_version)s')
                ],
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="prep"),
            util.ShellArg(
                command=util.Interpolate(
                    "scp {{ buildbot_scp_builds_get }} binaries/%(prop:debs_package_version)s/"
                ),
                haltOnFailure=True,
                flunkOnFailure=True,
                logfile="download")
        ],
        name="Fetching built artifacts from buildmaster",
        haltOnFailure=True,
        flunkOnFailure=True)

    debsBuild = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=util.Interpolate(
                    'echo "source library.sh\ndoOpencast %(prop:debs_package_version)s %(prop:branch)s %(prop:parent_revision)s" | tee build.sh'
                ),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='write'),
            util.ShellArg(
                command=['bash', 'build.sh'],
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='build'),
            util.ShellArg(
                command=util.Interpolate(
                    'echo "Opencast version %(prop:parent_revision)s packaged with version %(prop:deb_script_rev)s" | tee outputs/%(prop:parent_revision)s/revision.txt'
                ),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='revision')
        ],
        workdir="build",
        name="Build debs",
        haltOnFailure=True,
        flunkOnFailure=True)

    debsUpload = steps.ShellCommand(
        command=util.Interpolate(
            "scp -r outputs/%(prop:parent_revision)s/* {{ buildbot_scp_debs }}"
        ),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload debs to buildmaster")

    clean = TODO: Define how to clean the debs

    f_package_debs = util.BuildFactory()
    f_package_debs.addStep(
        steps.SetProperty(
            property="branch",
            value=branchInfo['branch'],
            name="Set regular branch name"))
    f_package_debs.addStep(
        steps.SetProperty(
            property="branch_pretty",
            value=branchname,
            name="Set pretty branch name"))
    f_package_debs.addStep(
        steps.SetProperty(
            property="debs_package_version",
            value=branchInfo['debsVersion'],
            name="Set Debian package version"))
    f_package_debs.addStep(debChecker)
    f_package_debs.addStep(debsClone)
    f_package_debs.addStep(debsUpdate)
    f_package_debs.addStep(debsVersion)
    f_package_debs.addStep(debsPrep)
    f_package_debs.addStep(debsFetch)
    f_package_debs.addStep(debsBuild)
    f_package_debs.addStep(debsUpload)
    f_package_debs.addStep(clean)

    return f_package_debs
