# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import schedulers, util
import common


def _getAnyBranchScheduler(name, builderNames, change_filter=None, properties=dict()):
    return schedulers.AnyBranchScheduler(
        name=name,
        # NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        treeStableTimer={{ stability_limit }},
        builderNames=builderNames,
        properties=properties,
        change_filter=change_filter)


def _getForceScheduler(props, prefix, builderNames):
    pretty_branch_name = props['branch_pretty']

    forceParams = [
        util.CodebaseParameter(
            "",
            label="Main repository",
            # will generate a combo box
            branch=util.FixedParameter(
                name="branch",
                default=props['git_branch_name'],
            ),
            # will generate nothing in the form, but revision, repository,
            # and project are needed by buildbot scheduling system so we
            # need to pass a value ("")
            revision=util.FixedParameter(name="revision", default="HEAD"),
            repository=util.FixedParameter(
                name="repository", default="{{ source_repo_url }}"),
            project=util.FixedParameter(name="project", default=""),
        ),
    ]

    # Note: This is a hack, but we need a unique name for the force schedulers, and it can't have special characters in it...
    return schedulers.ForceScheduler(
        name=prefix + pretty_branch_name[0:2].replace('.', 'x'),
        buttonName="Force Build",
        label="Force Build Settings",
        builderNames=builderNames,
        codebases=forceParams,

        # will generate a text input
        reason=util.StringParameter(
            name="reason",
            label="Reason:",
            required=False,
            size=80,
            default=""),

        # in case you don't require authentication this will display
        # input for user to type his name
        username=util.UserNameParameter(label="your name:", size=80))


def getPullRequestScheduler(props, pretty_branch_name):
    builderNames = [ pretty_branch_name + " Pull Request " + build_type + " JDK " + str(jdk) for build_type in [ 'Build', 'Reports' ] for jdk in common.getJDKBuilds(props)]
    builderNames.extend([
        pretty_branch_name + " Pull Request Markdown",
#        pretty_branch_name + " Pull Request Database Tests"
    ])

    pull_cf=util.ChangeFilter(category="pull", branch_re=props['git_branch_name'])

    return _getAnyBranchScheduler(name=pretty_branch_name + " Pull Requests",
                                   builderNames=builderNames,
                                   change_filter=pull_cf)


def _getBasicSchedulers(props):
    pretty_branch_name = props['branch_pretty']

    branch_cf = util.ChangeFilter(category=None, branch_re=props['git_branch_name'])

    schedDict = {}

    schedDict['prs'] = getPullRequestScheduler(props, pretty_branch_name)

    for build_type in [ "Build", "Reports" ]:
        for jdk in common.getJDKBuilds(props):
            sched = _getAnyBranchScheduler(
                name=common.getBuildWithJDK(pretty_branch_name, build_type, jdk),
                change_filter=branch_cf,
                properties=props,
                builderNames=[
                    common.getBuildWithJDK(pretty_branch_name, build_type, jdk),
            ])
            schedDict[build_type + str(jdk)] = sched

    sched = _getAnyBranchScheduler(
        name=pretty_branch_name + " Quick Build",
        change_filter=branch_cf,
        properties=props,
        builderNames=[
            pretty_branch_name + " Markdown",
#            pretty_branch_name + " Database Tests"
        ])
    schedDict["markdowndb"] = sched

    if str(props['package_all']).lower() != 'true':
        sched = schedulers.Nightly(
            name=pretty_branch_name + ' Package Generation',
            change_filter=branch_cf,
            hour={{nightly_build_hour}},
            onlyIfChanged=True,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " el7 RPM Packaging",
                pretty_branch_name + " el8 RPM Packaging"
            ])
    else:
        defaultJDK = common.getJDKBuilds(props)[0]
        sched = schedulers.Dependent(
            name=pretty_branch_name + " Packaging Generation",
            upstream=schedDict["Build" + str(defaultJDK)],
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " el7 RPM Packaging",
                pretty_branch_name + " el8 RPM Packaging"
            ])
    schedDict['package'] = sched

    return schedDict


def getSchedulers(props):

    pretty_branch_name = props['branch_pretty']

    sched_dict = _getBasicSchedulers(props)
    scheduler_list = list(sched_dict.values())

    if str(props['has_repo_builder']).lower() == 'true':
        repo = schedulers.Dependent(
            name=pretty_branch_name + ' Repository Generation',
            upstream=sched_dict['package'],
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " RPM Repository",
            ])
        scheduler_list.append(repo)

        if props['deploy_env']:
            scheduler_list.append(schedulers.Dependent(
                name=pretty_branch_name + " Ansible Deploy",
                upstream=repo,
                properties=props,
                builderNames=[pretty_branch_name + " Ansible Deploy"]))

    forceBuildNames = [common.getBuildWithJDK(pretty_branch_name, "Build", jdk) for jdk in common.getJDKBuilds(props)]
    forceBuild = _getForceScheduler(props, "ForceBuild", forceBuildNames)
    scheduler_list.append(forceBuild)

    tag_sched = schedulers.AnyBranchScheduler(
        name=pretty_branch_name + " Release",
        #Note: The branch_regex here is matching something like "11.1", so we use the major version (11), plus a static .*
        change_filter=util.ChangeFilter(category='tag', branch_re=props['pkg_major_version'] + ".*"),
        properties=props,
        builderNames=[pretty_branch_name + " Release"])
    scheduler_list.append(tag_sched)

    forceBuilders = [common.getBuildWithJDK(pretty_branch_name, "Reports", jdk) for jdk in common.getJDKBuilds(props, pretty_branch_name)]

    forceBuilders.extend([
        pretty_branch_name + " Markdown",
#        pretty_branch_name + " Database Tests",
        pretty_branch_name + " Debian Packaging",
        pretty_branch_name + " el7 RPM Packaging",
        pretty_branch_name + " el8 RPM Packaging"
    ])

    if props['has_repo_builder']:
#        forceBuilders.append(pretty_branch_name + " Debian Repository")
        forceBuilders.append(pretty_branch_name + " RPM Repository")
        if props['deploy_env']:
            forceBuilders.append(pretty_branch_name + " Ansible Deploy")

    forceOther = _getForceScheduler(props, "ForceBuildOther", forceBuilders)
    scheduler_list.append(forceOther)

    if props['package_all']:
        forcePackage = schedulers.Dependent(
            name=pretty_branch_name + " Force Packaging Generation",
            upstream=forceBuild,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " el7 RPM Packaging",
                pretty_branch_name + " el8 RPM Packaging"
            ])
        scheduler_list.append(forcePackage)

        forceRepo = schedulers.Dependent(
            name=pretty_branch_name + " Force Repository Generation",
            upstream=forceBuild,
            properties=props,
            builderNames=[
#                pretty_branch_name + " Debian Repository",
                pretty_branch_name + " RPM Repository",
            ])
        scheduler_list.append(forceRepo)

        if props['deploy_env']:
            forceAnsible = schedulers.Dependent(
                name=pretty_branch_name + " Force Ansible Deploy",
                upstream=forceBuild,
                properties=props,
                builderNames=[
                    pretty_branch_name + " Ansible Deploy"
                ])
            scheduler_list.append(forceAnsible)

    return scheduler_list
