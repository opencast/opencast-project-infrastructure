# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import schedulers, util

deployables = []
{% for branch in opencast %}
{%   if 'server' in opencast[branch] %}
deployables.append('{{ branch }}')
{%   endif %}
{% endfor %}


def getPullRequestSchedulers():
    return schedulers.AnyBranchScheduler(
        name="Pull Requests",
        # NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        treeStableTimer={{ stability_limit }},
        builderNames=[
            "Pull Request Build",
            "Pull Request Reports",
            "Pull Request Markdown",
            "Pull Request Database Tests"
        ],
        change_filter=util.ChangeFilter(category="pull"))


def _getBasicSchedulers(pretty_branch_name, git_branch_name):
    commits = schedulers.AnyBranchScheduler(
        name=pretty_branch_name + " Quick Build",
        change_filter=util.ChangeFilter(
            category=None, branch_re=git_branch_name),
        # NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        treeStableTimer={{ stability_limit }},
        builderNames=[
            pretty_branch_name + " Build",
            pretty_branch_name + " Markdown",
            pretty_branch_name + " Database Tests"
        ])

    reports = schedulers.AnyBranchScheduler(
        name=pretty_branch_name + " Reports",
        change_filter=util.ChangeFilter(
            category=None, branch_re=git_branch_name),
        # NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        treeStableTimer={{ stability_limit }},
        builderNames=[
            pretty_branch_name + " Reports",
        ])

{% if not package_all %}
    package = schedulers.Nightly(
        name=pretty_branch_name + ' Package Generation',
        change_filter=util.ChangeFilter(
            category=None, branch_re=git_branch_name),
        hour={{nightly_build_hour}},
        onlyIfChanged=True,
        builderNames=[
            pretty_branch_name + " Debian Packaging",
            pretty_branch_name + " RPM Packaging",
        ])
{% else %}
    package = schedulers.Dependent(
        name=pretty_branch_name + " Packaging Generation",
        upstream=commits,
        builderNames=[
            pretty_branch_name + " Debian Packaging",
            pretty_branch_name + " RPM Packaging"
        ])
{% endif %}

    return commits, reports, package


def getSchedulers(pretty_branch_name, git_branch_name):

    #TODO: This is all spaghetti, and should be refactored to something based on an Ansible/Python dictionary and some logic...

    commits, reports, package = _getBasicSchedulers(pretty_branch_name, git_branch_name)

    scheduler_list = [ commits, reports, package ]

{# Only defining the repository building and ansible deployment builders if the appropriate bits are present #}
{% if buildbot_has_repo_builder %}
    repo = schedulers.Dependent(
        name=pretty_branch_name + ' Repository Generation',
        upstream=package,
        builderNames=[
            pretty_branch_name + " Debian Repository",
            pretty_branch_name + " RPM Repository",
        ])
    scheduler_list.append(repo)

    if pretty_branch_name in deployables:
        deploy = schedulers.Dependent(
            name=pretty_branch_name + " Ansible Deploy",
            upstream=repo,
            builderNames=[pretty_branch_name + " Ansible Deploy"])

        scheduler_list.append(deploy)

{% endif %}


    forceBuilders = [
        pretty_branch_name + " Reports",
        pretty_branch_name + " Markdown",
        pretty_branch_name + " Database Tests",
        pretty_branch_name + " Debian Packaging",
        pretty_branch_name + " RPM Packaging"
    ]

{# Only defining the force repository building and ansible deployment builders if the appropriate bits are present #}
{% if buildbot_has_repo_builder %}
    forceBuilders.append(pretty_branch_name + " Debian Repository")
    forceBuilders.append(pretty_branch_name + " RPM Repository")
    if pretty_branch_name in deployables:
        forceBuilders.append(pretty_branch_name + " Ansible Deploy")
{% endif %}

    forceParams = [
        util.CodebaseParameter(
            "",
            label="Main repository",
            # will generate a combo box
            branch=util.FixedParameter(
                name="branch",
                default=git_branch_name,
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
    forceBuild = schedulers.ForceScheduler(
        name="ForceBuild" + pretty_branch_name[0],
        buttonName="Force Build",
        label="Force Build Settings",
        builderNames=[pretty_branch_name + " Build"],
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

    scheduler_list.append(forceBuild)

    forceOther = schedulers.ForceScheduler(
        name="ForceBuildOther" + pretty_branch_name[0],
        buttonName="Force Build",
        label="Force Build Settings",
        builderNames=forceBuilders,
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

    scheduler_list.append(forceOther)

{% if package_all %}
    forcePackage = schedulers.Dependent(
        name=pretty_branch_name + " Force Packaging Generation",
        upstream=forceBuild,
        builderNames=[
            pretty_branch_name + " Debian Packaging",
            pretty_branch_name + " RPM Packaging"
        ])
    scheduler_list.append(forcePackage)

    forceRepo = schedulers.Dependent(
        name=pretty_branch_name + " Force Repository Generation",
        upstream=forceBuild,
        builderNames=[
            pretty_branch_name + " Debian Repository",
            pretty_branch_name + " RPM Repository",
        ])
    scheduler_list.append(forceRepo)

    if pretty_branch_name in deployables:
        forceAnsible = schedulers.Dependent(
            name=pretty_branch_name + " Force Ansible Deploy",
            upstream=forceBuild,
            builderNames=[
                pretty_branch_name + " Ansible Deploy"
            ])
        scheduler_list.append(forceAnsible)
{% endif %}
    return scheduler_list
