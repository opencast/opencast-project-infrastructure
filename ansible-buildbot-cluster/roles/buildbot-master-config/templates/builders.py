# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import build
import reports
import markdown
import database
import debs
import rpms


def getPullRequestBuilder(workers):

  f_pr_build = build.getPullRequestPipeline()

  f_pr_reports = reports.getPullRequestPipeline()

  f_pr_markdown = markdown.getPullRequestPipeline()

  f_pr_db = database.getPullRequestPipeline()

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

  b_pr_db = util.BuilderConfig(
      name="Pull Request Database Tests",
      workernames=workers,
      factory=f_pr_db,
      collapseRequests=True)

  return [
    b_pr_build, b_pr_reports, b_pr_markdown, b_pr_db
  ]

@util.renderer
def renderShortRevision(props):
  shortrev = props.getProperty('got_revision')
  return shortrev[:9]

def getBuildersForBranch(deb_workers, rpm_workers, pretty_branch_name, git_branch_name, pkg_major_version, pkg_minor_version):
	
    props = {
        'pkg_major_version': pkg_major_version,
        'pkg_minor_version': pkg_minor_version,
        'branch_pretty': pretty_branch_name,
    }

    #Get the list of all workers.  This should be used in all cases unless there's a specific need (ie, debs, rpms)
    workers = deb_workers + rpm_workers

    f_build = build.getBuildPipeline()

    f_reports = reports.getBuildPipeline()

    f_markdown = markdown.getBuildPipeline()

    f_db = database.getBuildPipeline()

    f_package_debs = debs.getBuildPipeline()

    f_package_rpms = rpms.getBuildPipeline()


    b_build = util.BuilderConfig(
        name=pretty_branch_name + " Build",
        workernames=workers,
        factory=f_build,
        properties=props,
        collapseRequests=True)

    b_reports = util.BuilderConfig(
        name=pretty_branch_name + " Reports",
        workernames=workers,
        factory=f_reports,
        properties=props,
        collapseRequests=True)

    b_markdown = util.BuilderConfig(
        name=pretty_branch_name + " Markdown",
        workernames=workers,
        factory=f_markdown,
        properties=props,
        collapseRequests=True)

    b_db = util.BuilderConfig(
        name=pretty_branch_name + " Database Tests",
        workernames=workers,
        factory=f_db,
        properties=props,
        collapseRequests=True)

    b_package_debs = util.BuilderConfig(
        name=pretty_branch_name + " Debian Packaging",
        workernames=deb_workers,
        factory=f_package_debs,
        properties=props,
        collapseRequests=True)

    b_package_rpms = util.BuilderConfig(
        name=pretty_branch_name + " RPM Packaging",
        workernames=rpm_workers,
        factory=f_package_rpms,
        properties=props,
        collapseRequests=True)

    return [
        b_build, b_reports, b_markdown, b_db, b_package_debs, b_package_rpms
    ]
