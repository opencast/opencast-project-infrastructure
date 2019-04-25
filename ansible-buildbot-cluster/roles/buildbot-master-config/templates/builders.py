# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import build
import reports
import markdown
import database
import debs
import rpms
import deb_repo
import rpm_repo


mvn_lock = util.WorkerLock("mvn_lock",
                             maxCount=1)

db_lock = util.WorkerLock("db_lock",
                             maxCount=1)

deb_lock = util.WorkerLock("deb_lock",
                             maxCount=1)

rpm_lock = util.WorkerLock("rpm_lock",
                             maxCount=1)


def getPullRequestBuilder():

  f_pr_build = build.getPullRequestPipeline()

  f_pr_reports = reports.getPullRequestPipeline()

  f_pr_markdown = markdown.getPullRequestPipeline()

  f_pr_db = database.getPullRequestPipeline()

  b_pr_build = util.BuilderConfig(
      name="Pull Request Build",
      workernames=getWorkerList(),
      factory=f_pr_build,
      collapseRequests=True,
      locks=[mvn_lock.access('exclusive')])

  b_pr_reports = util.BuilderConfig(
      name="Pull Request Reports",
      workernames=getWorkerList(),
      factory=f_pr_reports,
      collapseRequests=True,
      locks=[mvn_lock.access('exclusive')])

  b_pr_markdown = util.BuilderConfig(
      name="Pull Request Markdown",
      workernames=getWorkerList(),
      factory=f_pr_markdown,
      collapseRequests=True)

  b_pr_db = util.BuilderConfig(
      name="Pull Request Database Tests",
      workernames=getWorkerList(),
      factory=f_pr_db,
      collapseRequests=True,
      locks=[db_lock.access('exclusive')])

  return [
    b_pr_build, b_pr_reports, b_pr_markdown, b_pr_db
  ]

@util.renderer
def renderShortRevision(props):
  shortrev = props.getProperty('got_revision')
  return shortrev[:9]

def getWorkerList(filterBy=None):
  workers = {
{% for worker in groups['workers'] %}
{% if hostvars[worker]['bifurcated'] is defined %}
    "{{ hostvars[worker]['name'] }}-deb": "debian",
    "{{ hostvars[worker]['name'] }}-rpm": "centos",
{% else %}
    "{{ hostvars[worker]['name'] }}": "{{ hostvars[worker]['docker_base'] }}",
{% endif %}
{% endfor %}
  }

  if None == filterBy:
    return list(workers.keys())
  else:
    return list(filter(lambda x: workers[x] == filterBy, workers))

def getBuildersForBranch(pretty_branch_name, git_branch_name, pkg_major_version, pkg_minor_version):

    props = {
        'pkg_major_version': pkg_major_version,
        'pkg_minor_version': pkg_minor_version,
        'branch_pretty': pretty_branch_name,
    }

    f_build = build.getBuildPipeline()
{% if package_all %}
    f_build.addStep(steps.Trigger(schedulerNames=[pretty_branch_name + " Packaging Triggerable"], name="Trigger packaging builds"))
{% endif %}

    f_reports = reports.getBuildPipeline()

    f_markdown = markdown.getBuildPipeline()

    f_db = database.getBuildPipeline()

    f_package_debs = debs.getBuildPipeline()

    f_package_rpms = rpms.getBuildPipeline()

    f_repo_debs = deb_repo.getBuildPipeline()

    f_repo_rpms = rpm_repo.getBuildPipeline()

    b_build = util.BuilderConfig(
        name=pretty_branch_name + " Build",
        workernames=getWorkerList(),
        factory=f_build,
        properties=props,
        collapseRequests=True,
        locks=[mvn_lock.access('exclusive')])

    b_reports = util.BuilderConfig(
        name=pretty_branch_name + " Reports",
        workernames=getWorkerList(),
        factory=f_reports,
        properties=props,
        collapseRequests=True,
        locks=[mvn_lock.access('exclusive')])

    b_markdown = util.BuilderConfig(
        name=pretty_branch_name + " Markdown",
        workernames=getWorkerList(),
        factory=f_markdown,
        properties=props,
        collapseRequests=True)

    b_db = util.BuilderConfig(
        name=pretty_branch_name + " Database Tests",
        workernames=getWorkerList(),
        factory=f_db,
        properties=props,
        collapseRequests=True,
        locks=[db_lock.access('exclusive')])

    b_package_debs = util.BuilderConfig(
        name=pretty_branch_name + " Debian Packaging",
        workernames=getWorkerList("debian"),
        factory=f_package_debs,
        properties=props,
        collapseRequests=True,
        locks=[deb_lock.access('exclusive')])

    b_package_rpms = util.BuilderConfig(
        name=pretty_branch_name + " RPM Packaging",
        workernames=getWorkerList("centos"),
        factory=f_package_rpms,
        properties=props,
        collapseRequests=True,
        locks=[rpm_lock.access('exclusive')])

    b_repo_debs = util.BuilderConfig(
        name=pretty_branch_name + " Debian Repository",
        workernames=getWorkerList("debian"),
        factory=f_repo_debs,
        properties=props,
        collapseRequests=True,
        locks=[deb_lock.access('exclusive')])

    b_repo_rpms = util.BuilderConfig(
        name=pretty_branch_name + " RPM Repository",
        workernames=getWorkerList("centos"),
        factory=f_repo_rpms,
        properties=props,
        collapseRequests=True,
        locks=[rpm_lock.access('exclusive')])

    return [
        b_build, b_reports, b_markdown, b_db, b_package_debs, b_package_rpms, b_repo_debs, b_repo_rpms
    ]
