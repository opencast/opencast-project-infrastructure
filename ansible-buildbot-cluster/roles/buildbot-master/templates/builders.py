# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import build
import reports
import markdown
import debs
import rpms


def getPullRequestBuilder():
  f_pre_build = build.getPullRequestPipeline()

  b_pr = util.BuilderConfig(name="Pull Request Build",
      workernames=workers,
      factory=f_pr_build, collapseRequests=True)

  return b_pr

def getBuildersForBranch(branchname, branchInfo):

    f_build = build.getBuildPipeline(branchname, brancheInfo)

    f_reports = reports.getBuildPipeline(branchname, brancheInfo)

    f_markdown = markdown.getBuildPipeline(branchname, branches[branchname])

    trigger_debs = steps.Trigger(
        schedulerNames=[branchName + " Debian Packaging"],
        waitForFinish=False,
        name="Trigger " + branchName + " Debian Packaging",
        set_properties={
            "parent_build": util.Property("buildnumber"),
            "parent_revision": util.Property("got_revision"),
            "branch": util.Property("branch"),
            "branch_pretty": util.Property("branch_pretty"),
            "build_timestamp": util.Property("build_timestamp")
        })

    trigger_rpms = steps.Trigger(
        schedulerNames=[branchName + " RPM Packaging"],
        waitForFinish=False,
        name="Trigger " + branchName + " RPM Packaging",
        set_properties={
            "parent_build": util.Property("buildnumber"),
            "parent_revision": util.Property("got_revision"),
            "branch": util.Property("branch"),
            "branch_pretty": util.Property("branch_pretty"),
            "build_timestamp": util.Property("build_timestamp")
        })

    f_nightly = build.getBuildPipeline(branchname, branchInfo)
    f_nightly.addStep(deb_trigger_step)
    f_nightly.addStep(rpm_trigger_step)

    f_package_debs = debs.getBuildPipeline(branchname, brancheInfo)

    f_package_rpms = rpms.getBuildPipeline(branchname, brancheInfo)

    b_build = util.BuilderConfig(
        name=branchname + " Build",
        workernames=workers,
        factory=f_build,
        collapseRequests=True)

    b_nightly = util.BuilderConfig(
        name=branchname + " Nightly",
        workernames=workers,
        factory=f_nightly,
        collapseRequests=True)

    b_reports = util.BuilderConfig(
        name=branchname + " Reports",
        workernames=workers,
        factory=f_reports,
        collapseRequests=True)

    b_javadocs = util.BuilderConfig(
        name=branchname + " Javadocs",
        workernames=workers,
        factory=f_javadocs,
        collapseRequests=True)

    b_markdown = util.BuilderConfig(
        name=branchname + " Markdown Docs",
        workernames=workers,
        factory=f_markdown,
        collapseRequests=True)

    b_package_debs = util.BuilderConfig(
        name=branchname + " Debian Packaging",
        workernames=workers,
        factory=f_package_debs,
        collapseRequests=True)

    b_package_rpms = util.BuilderConfig(
        name=branchname + " RPM Packaging",
        workernames=workers,
        factory=f_package_rpms,
        collapseRequests=True)

    return [
        b_build, b_nightly, b_reports, b_javadocs, b_markdown, b_package_debs, b_package_rpms
    ]
