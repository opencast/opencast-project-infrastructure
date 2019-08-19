# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util
import build
import reports
import markdown
import database
import debs
import rpms
import deb_repo
import rpm_repo
import ansible


mvn_lock = util.WorkerLock("mvn_lock", maxCount=1)

db_lock = util.WorkerLock("db_lock", maxCount=1)

deb_lock = util.WorkerLock("deb_lock", maxCount=1)

rpm_lock = util.WorkerLock("rpm_lock", maxCount=1)


# We're doing the filter here to remove blank entries (ie, "") since some of these lines in some cases don't yield
# results, but it's hard to keep from adding the front and end quotes in Jinja
workers = list(filter(lambda a: a, [
  {{ '\"' + groups['workers'] | map('extract', hostvars)
                                   | selectattr('only_repo_builder', 'undefined')
                                   | map(attribute='name') | join('\", \"') + '\"' }},
  {{ '\"' + groups['workers'] | map('extract', hostvars)
                                   | selectattr('only_repo_builder', 'defined')
                                   | selectattr('only_repo_builder', 'eq', 'False') | map(attribute='name') | join('\", \"') + '\"' }}
  ]))

repo_workers = list(filter(lambda a: a, [
  {{ '\"' + groups['workers'] | map('extract', hostvars)
                                   | selectattr('repo_builder', 'defined') | selectattr('repo_builder')
                                   | map(attribute='name') | join('\", \"') + '\"' }},
  {{ '\"' + groups['workers'] | map('extract', hostvars)
                                   | selectattr('only_repo_builder', 'defined') | selectattr('only_repo_builder')
                                   | map(attribute='name') | join('\", \"') + '\"' }}
]))


def getPullRequestBuilder():

    f_pr_build = build.getPullRequestPipeline()

    f_pr_reports = reports.getPullRequestPipeline()

    f_pr_markdown = markdown.getPullRequestPipeline()

    f_pr_db = database.getPullRequestPipeline()

    b_pr_build = util.BuilderConfig(
            name="Pull Request Build",
            workernames=workers,
            factory=f_pr_build,
            collapseRequests=True,
            locks=[mvn_lock.access('exclusive')])

    b_pr_reports = util.BuilderConfig(
            name="Pull Request Reports",
            workernames=workers,
            factory=f_pr_reports,
            collapseRequests=True,
            locks=[mvn_lock.access('exclusive')])

    b_pr_markdown = util.BuilderConfig(
            name="Pull Request Markdown",
            workernames=workers,
            factory=f_pr_markdown,
            collapseRequests=True)

    b_pr_db = util.BuilderConfig(
            name="Pull Request Database Tests",
            workernames=workers,
            factory=f_pr_db,
            collapseRequests=True,
            locks=[db_lock.access('exclusive')])

    return [
        b_pr_build, b_pr_reports, b_pr_markdown, b_pr_db
    ]


def getBuildersForBranch(pretty_branch_name, git_branch_name, pkg_major_version, pkg_minor_version):

    props = {
        'pkg_major_version': pkg_major_version,
        'pkg_minor_version': pkg_minor_version,
        'branch_pretty': pretty_branch_name,
        'signing_key': '{{ signing_key_id }}'
    }

    deb_props = dict(props)
    deb_props['image'] = "debian"

    cent_props = dict(props)
    cent_props['image'] = "centos"

    f_build = build.getBuildPipeline()

    f_reports = reports.getBuildPipeline()

    f_markdown = markdown.getBuildPipeline()

    f_db = database.getBuildPipeline()

    f_package_debs = debs.getBuildPipeline()

    f_package_rpms = rpms.getBuildPipeline()

    f_repo_debs = deb_repo.getBuildPipeline()

    f_repo_rpms = rpm_repo.getBuildPipeline()

    f_ansible_deploy = ansible.getBuildPipeline()

    b_build = util.BuilderConfig(
            name=pretty_branch_name + " Build",
            workernames=workers,
            factory=f_build,
            properties=props,
            collapseRequests=True,
            locks=[mvn_lock.access('exclusive')])

    b_reports = util.BuilderConfig(
            name=pretty_branch_name + " Reports",
            workernames=workers,
            factory=f_reports,
            properties=props,
            collapseRequests=True,
            locks=[mvn_lock.access('exclusive')])

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
            collapseRequests=True,
            locks=[db_lock.access('exclusive')])

    b_package_debs = util.BuilderConfig(
            name=pretty_branch_name + " Debian Packaging",
            workernames=workers,
            factory=f_package_debs,
            properties=deb_props,
            collapseRequests=True,
            locks=[deb_lock.access('exclusive')])

    b_package_rpms = util.BuilderConfig(
            name=pretty_branch_name + " RPM Packaging",
            workernames=workers,
            factory=f_package_rpms,
            properties=cent_props,
            collapseRequests=True,
            locks=[rpm_lock.access('exclusive')])

    builders = [
            b_build, b_reports, b_markdown, b_db, b_package_debs, b_package_rpms
    ]

    if len(repo_workers) > 0:
        b_repo_debs = util.BuilderConfig(
            name=pretty_branch_name + " Debian Repository",
            workernames=repo_workers,
            factory=f_repo_debs,
            properties=deb_props,
            collapseRequests=True,
            locks=[deb_lock.access('exclusive')])

        b_repo_rpms = util.BuilderConfig(
            name=pretty_branch_name + " RPM Repository",
            workernames=repo_workers,
            factory=f_repo_rpms,
            properties=cent_props,
            collapseRequests=True,
            locks=[rpm_lock.access('exclusive')])

        builders.append(b_repo_debs)
        builders.append(b_repo_rpms)

        deployables = {}
{% for branch in opencast %}
{%   if 'server' in opencast[branch] %}
        deployables['{{ branch }}'] = "{{ opencast[branch]['server'] }}"
{%   endif %}
{% endfor %}

        if pretty_branch_name in deployables:
            deploy_props = dict(props)
            deploy_props['deploy_env'] = deployables[pretty_branch_name]
            deploy_props['deploy_suite'] = '{{ repo_deploy_suite }}'
            deploy_props['package_repo_host'] = "{{ repo_host }}"
            deploy_props['key_url'] = "{{ key_url }}"
            deploy_props['key_id'] = "{{ key_id }}"

            b_ansible_deploy = util.BuilderConfig(
                name=pretty_branch_name + " Ansible Deploy",
                workernames=workers,
                factory=f_ansible_deploy,
                properties=deploy_props,
                collapseRequests=True)

            builders.append(b_ansible_deploy)

    return builders
