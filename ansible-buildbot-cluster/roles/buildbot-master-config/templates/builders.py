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

  f_pr_reports = reports.getPullRequestPipeline()

  f_pr_markdown = markdown.getPullRequestPipeline()

  b_pr_build = util.BuilderConfig(
      name="Pull Request Build",
      workernames=workers,
      factory=f_pr_build,
      collapseRequests=True)

  b_pr_reports = util.BuilderConfig(
      name="Pull Request Reports",
      workernames=workers,
      factory=f_pr_reports,
      collapseRequests=True)

  b_pr_markdown = util.BuilderConfig(
      name="Pull Request Markdown",
      workernames=workers,
      factory=f_pr_markdown,
      collapseRequests=True)

  return [
    b_pr_build, b_pr_reports, b_pr_markdown
  ]

def getTriggerStep(scheduler_name, debs_version, rpms_version):
  return steps.Trigger(
            schedulerNames=[scheduler_name],
            waitForFinish=False,
            name="Trigger " + scheduler_name,
            set_properties={
                 "got_revision": util.Property("got_revision"), #used in the packaging scripts
                 "branch_pretty": util.Property("branch_pretty"), #used for deploying things
                 "debs_package_version": debs_version, #pretty version name for deb packaging
                 "major_version": rpms_version #used for rpm packaging
            })

def getBuildersForBranch(deb_workers, rpm_workers, pretty_branch_name, git_branch_name, debs_version, rpms_version):
	
    #Get the list of all workers.  This should be used in all cases unless there's a specific need (ie, debs, rpms)
    workers = deb_workers + rpm_workers

    f_build = build.getBuildPipeline()

    f_reports = reports.getBuildPipeline()

    f_markdown = markdown.getBuildPipeline()

    f_nightly = build.getBuildPipeline()

    for buildType in ("Debian Packaging", "RPM Packaging"):
      scheduler_name = pretty_branch_name + " " + buildType
      f_nightly.addStep(getTriggerStep(scheduler_name, debs_version, rpms_version))

    f_package_debs = debs.getBuildPipeline()

    f_package_rpms = rpms.getBuildPipeline()


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
        workernames=deb_workers,
        factory=f_package_debs,
        collapseRequests=True)

    b_package_rpms = util.BuilderConfig(
        name=pretty_branch_name + " RPM Packaging",
        workernames=rpm_workers,
        factory=f_package_rpms,
        collapseRequests=True)

    return [
        b_build, b_nightly, b_reports, b_markdown, b_package_debs, b_package_rpms
    ]
