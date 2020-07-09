# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util
import random
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

    b_pr_build = util.BuilderConfig(
        name="Pull Request Build",
        workernames=workers,
        factory=build.getPullRequestPipeline(),
        collapseRequests=True,
        locks=[mvn_lock.access('exclusive')])

    b_pr_reports = util.BuilderConfig(
        name="Pull Request Reports",
        workernames=workers,
        factory=reports.getPullRequestPipeline(),
        collapseRequests=True,
        locks=[mvn_lock.access('exclusive')])

    b_pr_markdown = util.BuilderConfig(
        name="Pull Request Markdown",
        workernames=workers,
        factory=markdown.getPullRequestPipeline(),
        collapseRequests=True)

    b_pr_db = util.BuilderConfig(
        name="Pull Request Database Tests",
        workernames=workers,
        factory=database.getPullRequestPipeline(),
        collapseRequests=True,
        locks=[db_lock.access('exclusive')])

    return [
        b_pr_build, b_pr_reports, b_pr_markdown, b_pr_db
    ]


def getBuildersForBranch(props):

    pretty_branch_name = props['branch_pretty']

    deb_props = dict(props)
    deb_props['image'] = random.choice({{ docker_debian_worker_images }})

    cent_props = dict(props)
    cent_props['image'] = random.choice({{ docker_centos_worker_images }})

    jdk8_props = dict(props)
    jdk8_props['jdk'] = 8

    b_build = util.BuilderConfig(
        name=pretty_branch_name + " Build",
        workernames=workers,
        factory=build.getBuildPipeline(),
        properties=jdk8_props,
        collapseRequests=True,
        locks=[mvn_lock.access('exclusive')])

    b_reports = util.BuilderConfig(
        name=pretty_branch_name + " Reports",
        workernames=workers,
        factory=reports.getBuildPipeline(),
        properties=jdk8_props,
        collapseRequests=True,
        locks=[mvn_lock.access('exclusive')])

    b_markdown = util.BuilderConfig(
        name=pretty_branch_name + " Markdown",
        workernames=workers,
        factory=markdown.getBuildPipeline(),
        properties=props,
        collapseRequests=True)

    b_db = util.BuilderConfig(
        name=pretty_branch_name + " Database Tests",
        workernames=workers,
        factory=database.getBuildPipeline(),
        properties=props,
        collapseRequests=True,
        locks=[db_lock.access('exclusive')])

    b_package_debs = util.BuilderConfig(
        name=pretty_branch_name + " Debian Packaging",
        workernames=workers,
        factory=debs.getBuildPipeline(),
        properties=deb_props,
        collapseRequests=True,
        locks=[deb_lock.access('exclusive')])

    b_package_rpms = util.BuilderConfig(
        name=pretty_branch_name + " RPM Packaging",
        workernames=workers,
        factory=rpms.getBuildPipeline(),
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
            factory=deb_repo.getBuildPipeline(),
            properties=deb_props,
            collapseRequests=True,
            locks=[deb_lock.access('exclusive')])

        b_repo_rpms = util.BuilderConfig(
            name=pretty_branch_name + " RPM Repository",
            workernames=repo_workers,
            factory=rpm_repo.getBuildPipeline(),
            properties=cent_props,
            collapseRequests=True,
            locks=[rpm_lock.access('exclusive')])

        builders.append(b_repo_debs)
        builders.append(b_repo_rpms)

        if props['deploy_env']:
            deploy_props = dict(props)
            deploy_props['deploy_suite'] = '{{ repo_deploy_suite }}'
            deploy_props['package_repo_host'] = "{{ repo_host }}"
            deploy_props['key_url'] = "{{ key_url }}"
            deploy_props['key_id'] = "{{ key_id }}"

            b_ansible_deploy = util.BuilderConfig(
                name=pretty_branch_name + " Ansible Deploy",
                workernames=workers,
                factory=ansible.getBuildPipeline(),
                properties=deploy_props,
                collapseRequests=True)

            builders.append(b_ansible_deploy)

    return builders
