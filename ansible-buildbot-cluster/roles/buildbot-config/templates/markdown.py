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

    gruntCheck = common.shellSequence(
        commands=[
            common.shellArg(
                command=['npm', 'install'],
                logfile='npm_install'),
            common.shellArg(
                command=['./node_modules/grunt/bin/grunt'],
                haltOnFailure=False,
                logfile='grunt'),
        ],
        workdir="build/docs/guides",
        name="Check Markdown doc formatting with grunt",
        haltOnFailure=False,
        doStepIf=lambda step: step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") == "True",
        hideStepIf=lambda results, step: not (step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") == "True"))

    npmCheck = common.shellSequence(
        commands=[
            common.shellArg(
                command=['npm', 'install'],
                logfile='npm_install'),
            common.shellArg(
                command=['npm', 'test'],
                haltOnFailure=False,
                logfile='markdown-cli'),
        ],
        workdir="build/docs/guides",
        name="Check Markdown doc formatting with markdown-cli",
        haltOnFailure=False,
        doStepIf=lambda step: step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") != "True",
        hideStepIf=lambda results, step: not (step.getProperty("npmConfigExists") == "True" and step.getProperty("gruntConfigExists") != "True"))

    build = common.shellSequence(
        commands=[
            common.shellArg(
                command='cd admin && mkdocs build && cd ..',
                haltOnFailure=False,
                logfile='admin'),
            common.shellArg(
                command='cd developer && mkdocs build && cd ..',
                haltOnFailure=False,
                logfile='developer'),
            common.shellArg(
                command='cd user && mkdocs build && cd ..',
                haltOnFailure=False,
                logfile='user'),
        ],
        env={
            "LC_ALL": "en_US.utf-8",
            "LANG": "en_US.utf-8"
        },
        workdir="build/docs/guides",
        name="Build Markdown docs")

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
                 util.Interpolate(
                     os.path.normpath("{{ deployed_markdown }}")),
                 util.Interpolate(
                     os.path.normpath("{{ deployed_markdown_symlink_base }}")),
                 ],
        flunkOnFailure=True,
        name="Prep relevant directories on buildmaster")

    upload = common.shellSequence(
        commands=[
            common.shellArg(
                command=util.Interpolate(
                    "scp -r admin/site {{ buildbot_scp_markdown }}/admin"),
                haltOnFailure=False,
                logfile='admin'),
            common.shellArg(
                command=util.Interpolate(
                    "scp -r developer/site {{ buildbot_scp_markdown }}/developer"
                ),
                haltOnFailure=False,
                logfile='developer'),
            common.shellArg(
                command=util.Interpolate(
                    "scp -r user/site {{ buildbot_scp_markdown }}/user"),
                haltOnFailure=False,
                logfile='user'),
        ],
        workdir="build/docs/guides",
        name="Upload Markdown docs to buildmaster",
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
