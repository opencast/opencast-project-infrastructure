# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import schedulers, util

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
        name=prefix + pretty_branch_name[0],
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

def getPullRequestScheduler():
    #NB: We're returning a list here since master.cfg is using List.extend()
    return [_getAnyBranchScheduler(name="Pull Requests",
                                  builderNames=[
                                      "Pull Request Build",
                                      "Pull Request Reports",
                                      "Pull Request Markdown",
                                      "Pull Request Database Tests"
                                  ],
                                  change_filter=util.ChangeFilter(category="pull"))]


def _getBasicSchedulers(props):
    pretty_branch_name = props['branch_pretty']
    git_branch_name = props['git_branch_name']

    branch_cf = util.ChangeFilter(category=None, branch_re=git_branch_name)

    commits = _getAnyBranchScheduler(
        name=pretty_branch_name + " Quick Build",
        change_filter=branch_cf,
        properties=props,
        builderNames=[
            pretty_branch_name + " Build",
            pretty_branch_name + " Markdown",
            pretty_branch_name + " Database Tests"
        ])

    reports = _getAnyBranchScheduler(
        name=pretty_branch_name + " Reports",
        change_filter=branch_cf,
        properties=props,
        builderNames=[
            pretty_branch_name + " Reports",
        ])

    if props['package_all']:
        package = schedulers.Nightly(
            name=pretty_branch_name + ' Package Generation',
            change_filter=branch_cf,
            hour={{nightly_build_hour}},
            onlyIfChanged=True,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " RPM Packaging",
            ])
    else:
        package = schedulers.Dependent(
            name=pretty_branch_name + " Packaging Generation",
            upstream=commits,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " RPM Packaging"
            ])

    return commits, reports, package


def getSchedulers(props):

    pretty_branch_name = props['branch_pretty']

    commits, reports, package = _getBasicSchedulers(props)

    scheduler_list = [ commits, reports, package ]

    if props['has_repo_builder']:
        repo = schedulers.Dependent(
            name=pretty_branch_name + ' Repository Generation',
            upstream=package,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Repository",
                pretty_branch_name + " RPM Repository",
            ])
        scheduler_list.append(repo)

        if props['deploy_env']:
            deploy = schedulers.Dependent(
                name=pretty_branch_name + " Ansible Deploy",
                upstream=repo,
                properties=props,
                builderNames=[pretty_branch_name + " Ansible Deploy"])

            scheduler_list.append(deploy)

    forceBuilders = [
        pretty_branch_name + " Reports",
        pretty_branch_name + " Markdown",
        pretty_branch_name + " Database Tests",
        pretty_branch_name + " Debian Packaging",
        pretty_branch_name + " RPM Packaging"
    ]

    if props['has_repo_builder']:
        forceBuilders.append(pretty_branch_name + " Debian Repository")
        forceBuilders.append(pretty_branch_name + " RPM Repository")
        if props['deploy_env']:
            forceBuilders.append(pretty_branch_name + " Ansible Deploy")

    forceBuild = _getForceScheduler(props, "ForceBuild", [pretty_branch_name + " Build"])
    scheduler_list.append(forceBuild)

    forceOther = _getForceScheduler(props, "ForceBuildOther", forceBuilders)
    scheduler_list.append(forceOther)

    if props['package_all']:
        forcePackage = schedulers.Dependent(
            name=pretty_branch_name + " Force Packaging Generation",
            upstream=forceBuild,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Packaging",
                pretty_branch_name + " RPM Packaging"
            ])
        scheduler_list.append(forcePackage)

        forceRepo = schedulers.Dependent(
            name=pretty_branch_name + " Force Repository Generation",
            upstream=forceBuild,
            properties=props,
            builderNames=[
                pretty_branch_name + " Debian Repository",
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
