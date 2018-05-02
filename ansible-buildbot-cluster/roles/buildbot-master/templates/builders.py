# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import build
import reports
import markdown
import debs
import rpms


def getPullRequestBuilder(workers):

  f_pr_build = build.getPullRequestPipeline()

  b_pr = util.BuilderConfig(name="Pull Request Build",
      workernames=workers,
      factory=f_pr_build, collapseRequests=True)

  return b_pr

def getTriggerStep(scheduler_name):
  return steps.Trigger(
            schedulerNames=[scheduler_name],
            waitForFinish=False,
            name="Trigger " + scheduler_name,
            set_properties={
                 "parent_build": util.Property("buildnumber"),
                 "parent_revision": util.Property("got_revision"),
                 "branch": util.Property("branch"),
                 "branch_pretty": util.Property("branch_pretty"),
                 "build_timestamp": util.Property("build_timestamp"),
                 "debs_package_version": util.Property("debs_package_version")
            })

def getBuildersForBranch(workers, pretty_branch_name, git_branch_name, debs_version):

    f_parent = util.BuildFactory()
    f_parent.addStep(
        steps.SetProperty(
            property="branch",
            value=git_branch_name,
            name="Set regular branch name"))
    f_parent.addStep(
        steps.SetProperty(
            property="branch_pretty",
            value=pretty_branch_name,
            name="Set pretty branch name"))
    f_parent.addStep(
        steps.SetProperty(
            property="debs_package_version",
            value=debs_version,
            name="Set Debian packaging version"))
    f_parent.addStep(
        steps.SetPropertyFromCommand(
            command="date -u +%FT%H-%M-%S",
            property="build_timestamp",
            flunkOnFailure=True,
            warnOnFailure=True,
            haltOnFailure=True,
            name="Get build timestamp"))
    for buildType in ("Build", "Reports", "Markdown"):
      scheduler_name = pretty_branch_name + " " + buildType
      f_parent.addStep(getTriggerStep(scheduler_name))

ASDF
nightly needs to kick off the build, markdown and reports, then wait, then kick off the rpms and debs.  Alt: have the build kick the packaging off
    f_build = build.getBuildPipeline()

    f_reports = reports.getBuildPipeline()

    f_markdown = markdown.getBuildPipeline()

    f_nightly = build.getBuildPipeline()

    for buildType in ("Debian Packaging", "RPM Packaging"):
      scheduler_name = pretty_branch_name + " " + buildType
      f_nightly.addStep(getTriggerStep(scheduler_name))

    f_package_debs = debs.getBuildPipeline()

    f_package_rpms = rpms.getBuildPipeline()


    b_entrypoint = util.BuilderConfig(
        name=pretty_branch_name + " Commits",
        workernames=workers,
        factory=f_parent,
        collapseRequests=True)

    b_build = util.BuilderConfig(
        name=pretty_branch_name + " Build",
        workernames=workers,
        factory=f_build,
        collapseRequests=True)

    b_nightly = util.BuilderConfig(
        name=pretty_branch_name + " Nightly",
        workernames=workers,
        factory=f_nightly,
        collapseRequests=True)

    b_reports = util.BuilderConfig(
        name=pretty_branch_name + " Reports",
        workernames=workers,
        factory=f_reports,
        collapseRequests=True)

    b_markdown = util.BuilderConfig(
        name=pretty_branch_name + " Markdown",
        workernames=workers,
        factory=f_markdown,
        collapseRequests=True)

    b_package_debs = util.BuilderConfig(
        name=pretty_branch_name + " Debian Packaging",
        workernames=workers,
        factory=f_package_debs,
        collapseRequests=True)

    b_package_rpms = util.BuilderConfig(
        name=pretty_branch_name + " RPM Packaging",
        workernames=workers,
        factory=f_package_rpms,
        collapseRequests=True)

    return [
        b_entrypoint, b_build, b_nightly, b_reports, b_markdown, b_package_debs, b_package_rpms
    ]
