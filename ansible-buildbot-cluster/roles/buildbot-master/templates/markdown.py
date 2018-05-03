# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import common


def getBuildPipeline():

    check = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['npm', 'install'],
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='npm_install'),
            util.ShellArg(
                command=['node_modules/grunt/bin/grunt'],
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='grunt'),
        ],
        workdir="docs/guides",
        name="Check Markdown doc formatting",
        haltOnFailure=True,
        flunkOnFailure=True)

    build = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command='cd admin && mkdocs build && cd ..',
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='admin'),
            util.ShellArg(
                command='cd developer && mkdocs build && cd ..',
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='developer'),
            util.ShellArg(
                command='cd user && mkdocs build && cd ..',
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='user'),
        ],
        workdir="docs/guides",
        name="Build Markdown docs",
        haltOnFailure=True,
        flunkOnFailure=True)

    upload = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=util.Interpolate(
                    "scp -r admin/site {{ buildbot_scp_markdown }}/admin"),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='admin'),
            util.ShellArg(
                command=util.Interpolate(
                    "scp -r developer/site {{ buildbot_scp_markdown }}/developer"
                ),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='developer'),
            util.ShellArg(
                command=util.Interpolate(
                    "scp -r user/site {{ buildbot_scp_markdown }}/user"),
                flunkOnFailure=True,
                warnOnFailure=True,
                haltOnFailure=True,
                logfile='user'),
        ],
        workdir="docs/guides",
        name="Upload Markdown docs to buildmaster",
        haltOnFailure=True,
        flunkOnFailure=True)


    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(check)
    f_build.addStep(build)
    f_build.addStep(common.getMasterPrep())
    f_build.addStep(common.getPermissionsFix())
    f_build.addStep(upload)
    f_build.addStep(common.getClean())

    return f_build
