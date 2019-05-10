# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

def __getBasePipeline(): 

    enable = steps.SetPropertyFromCommand(
        command='[ -f docs/guides/package.json ] && echo True || echo False',
        property="npmConfigExists",
        name="Check mkdocs version support")

    grunt = steps.SetPropertyFromCommand(
        command='[ -f docs/guides/Gruntfile.js ] && echo True || echo False',
        property="gruntConfigExists",
        name="Check Grunt config file existence")

    gruntCheck = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['npm', 'install'],
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='npm_install'),
            util.ShellArg(
                command=['./node_modules/grunt/bin/grunt'],
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='grunt'),
        ],
        workdir="build/docs/guides",
        name="Check Markdown doc formatting with grunt",
        haltOnFailure=False,
        flunkOnFailure=True,
        doStepIf=lambda step: step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") == "True",
        hideStepIf=lambda results, step: not (step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") == "True"))

    npmCheck = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=['npm', 'install'],
                flunkOnFailure=True,
                haltOnFailure=True,
                logfile='npm_install'),
            util.ShellArg(
                command=['npm', 'test'],
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='markdown-cli'),
        ],
        workdir="build/docs/guides",
        name="Check Markdown doc formatting with markdown-cli",
        haltOnFailure=False,
        flunkOnFailure=True,
        doStepIf=lambda step: step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") != "True",
        hideStepIf=lambda results, step: not (step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") != "True"))



    build = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command='cd admin && mkdocs build && cd ..',
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='admin'),
            util.ShellArg(
                command='cd developer && mkdocs build && cd ..',
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='developer'),
            util.ShellArg(
                command='cd user && mkdocs build && cd ..',
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='user'),
        ],
        workdir="build/docs/guides",
        name="Build Markdown docs",
        haltOnFailure=True,
        flunkOnFailure=True)


    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(enable)
    f_build.addStep(grunt)
    f_build.addStep(gruntCheck)
    f_build.addStep(npmCheck)
    f_build.addStep(build)

    return f_build

def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline():

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_markdown }}")),
                util.Interpolate(os.path.normpath("{{ deployed_markdown_symlink_base }}")),
        ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    upload = steps.ShellSequence(
        commands=[
            util.ShellArg(
                command=util.Interpolate(
                    "scp -r admin/site {{ buildbot_scp_markdown }}/admin"),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='admin'),
            util.ShellArg(
                command=util.Interpolate(
                    "scp -r developer/site {{ buildbot_scp_markdown }}/developer"
                ),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='developer'),
            util.ShellArg(
                command=util.Interpolate(
                    "scp -r user/site {{ buildbot_scp_markdown }}/user"),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='user'),
        ],
        workdir="build/docs/guides",
        name="Upload Markdown docs to buildmaster",
        haltOnFailure=True,
        flunkOnFailure=True,
        doStepIf=lambda step: step.getProperty("npmConfigExists") == "True")

    updateMarkdown = steps.MasterShellCommand(
        command=util.Interpolate(
            "rm -f {{ deployed_markdown_symlink }} && ln -s {{ deployed_markdown }} {{ deployed_markdown_symlink }}"
        ),
        flunkOnFailure=True,
        name="Deploy Markdown")


    f_build = __getBasePipeline()
    f_build.addStep(masterPrep)
    f_build.addStep(upload)
    f_build.addStep(updateMarkdown)
    f_build.addStep(common.getClean())

    return f_build
