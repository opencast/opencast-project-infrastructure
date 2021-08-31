# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util
import random
import common
import build
import reports
import markdown
import database
import debs
import rpms
import deb_repo
import rpm_repo
import ansible


#One of each of these per worker at a time
mvn_lock = util.WorkerLock("mvn_lock", maxCount=1)
db_lock = util.WorkerLock("db_lock", maxCount=1)

#These are used for the repository generation builders
#of which there must only be a single one running at a time across the whole cluster
deb_lock = util.MasterLock("deb_lock", maxCount=1)
rpm_lock = util.MasterLock("rpm_lock", maxCount=1)


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


def getPullRequestBuilder(props, pretty_branch_name):

    builders = []

    for jdk in common.getJDKBuilds(props, pretty_branch_name):
        jdk_props = dict(props)
        jdk_props['jdk'] = str(jdk)
        for build_type in ["Build", "Reports"]:
            builders.append(util.BuilderConfig(
                name=pretty_branch_name + " Pull Request " + build_type + " JDK " + str(jdk),
                workernames=workers,
                factory=build.getPullRequestPipeline(),
                collapseRequests=True,
                properties=jdk_props,
                locks=[mvn_lock.access('exclusive')]))


    builders.append(util.BuilderConfig(
        name=pretty_branch_name + " Pull Request Markdown",
        workernames=workers,
        factory=markdown.getPullRequestPipeline(),
        properties=props,
        collapseRequests=True))

#    builders.append(util.BuilderConfig(
#        name=pretty_branch_name + " Pull Request Database Tests",
#        workernames=workers,
#        factory=database.getPullRequestPipeline(),
#        properties=props,
#        collapseRequests=True,
#        locks=[db_lock.access('exclusive')]))

    return builders


def getBuildersForBranch(props):

    pretty_branch_name = props['branch_pretty']

    deb_props = dict(props)
    deb_props['image'] = random.choice({{ docker_debian_worker_images }})

    cent_props = dict(props)
    cent_props['image'] = random.choice({{ docker_centos_worker_images }})

    builders = getPullRequestBuilder(props, pretty_branch_name)

    #Only one maven build, per branch, at a time
    branch_mvn_lock = util.MasterLock(pretty_branch_name + "mvn_lock")

    for jdk in common.getJDKBuilds(props, pretty_branch_name):
        jdk_props = dict(props)
        jdk_props['jdk'] = str(jdk)
        for build_type in ["Build", "Reports"]:
            builders.append(util.BuilderConfig(
                name=pretty_branch_name + " " + build_type + " JDK " + str(jdk),
                workernames=workers,
                factory=build.getBuildPipeline(),
                properties=jdk_props,
                collapseRequests=True,
                #A note on these locks: We want a single maven build per branch,
                # AND a single maven build per worker
                locks=[mvn_lock.access('exclusive'), branch_mvn_lock.access('exclusive')]))

    builders.append(util.BuilderConfig(
        name=pretty_branch_name + " Markdown",
        workernames=workers,
        factory=markdown.getBuildPipeline(),
        properties=props,
        collapseRequests=True))

#    builders.append(util.BuilderConfig(
#        name=pretty_branch_name + " Database Tests",
#        workernames=workers,
#        factory=database.getBuildPipeline(),
#        properties=props,
#        collapseRequests=True,
#        locks=[db_lock.access('exclusive')]))

    builders.append(util.BuilderConfig(
        name=pretty_branch_name + " Debian Packaging",
        workernames=workers,
        factory=debs.getBuildPipeline(),
        properties=deb_props,
        collapseRequests=True))

    for distro in ("7", "8"):
        el_props = dict(props)
        el_props['image'] = f"cent{distro}"

        if "Develop" == pretty_branch_name:
            #Set the RPM branch to master
            el_props['rpmspec_override'] = "master"
            #Override/set a bunch of the build props since the RPM's dont relaly have a develop...

        builders.append(util.BuilderConfig(
            name=pretty_branch_name + f" el{distro} RPM Packaging",
            workernames=workers,
            factory=rpms.getBuildPipeline(),
            properties=el_props,
            collapseRequests=True))

    if len(repo_workers) > 0:
        builders.append(util.BuilderConfig(
            name=pretty_branch_name + " Debian Repository",
            workernames=repo_workers,
            factory=deb_repo.getBuildPipeline(),
            properties=deb_props,
            collapseRequests=True,
            locks=[deb_lock.access('exclusive')]))

        builders.append(util.BuilderConfig(
            name=pretty_branch_name + " RPM Repository",
            workernames=repo_workers,
            factory=rpm_repo.getBuildPipeline(),
            properties=cent_props,
            collapseRequests=True,
            locks=[rpm_lock.access('exclusive')]))

        if props['deploy_env']:
            deploy_props = dict(props)
            deploy_props['deploy_suite'] = '{{ repo_deploy_suite }}'
            deploy_props['package_repo_host'] = "{{ repo_host }}"
            deploy_props['key_url'] = "{{ key_url }}"
            deploy_props['key_id'] = "{{ key_id }}"

            builders.append(util.BuilderConfig(
                name=pretty_branch_name + " Ansible Deploy",
                workernames=workers,
                factory=ansible.getBuildPipeline(),
                properties=deploy_props,
                collapseRequests=True,
                #Ensure that no one is changing the package databases while we're deploying!
                locks=[deb_lock.access('exclusive'), rpm_lock.access('exclusive')]))

    return builders
