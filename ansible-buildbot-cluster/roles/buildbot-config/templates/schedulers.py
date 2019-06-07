# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *


def getPullRequestSchedulers():
    return schedulers.AnyBranchScheduler(
        name="Pull Requests",
        treeStableTimer={{stability_limit}},  #NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        builderNames=[
            "Pull Request Build",
            "Pull Request Reports",
            "Pull Request Markdown",
            "Pull Request Database Tests"
        ],
        change_filter=util.ChangeFilter(category="pull"))


def getSchedulers(pretty_branch_name, git_branch_name):

    scheduler_list = []

    commits_branch = schedulers.AnyBranchScheduler(
        name=pretty_branch_name,
        change_filter=util.ChangeFilter(
            category=None, branch_re=git_branch_name),
        treeStableTimer={{stability_limit}},  #NB: Do not make this a string, a horribly unclear error occurs and nothing works for this scheduler...
        builderNames=[
            pretty_branch_name + " Build",
            pretty_branch_name + " Reports",
            pretty_branch_name + " Markdown",
            pretty_branch_name + " Database Tests"
        ])

    nightly_branch = schedulers.Nightly(
        name=pretty_branch_name + ' Nightly',
        change_filter=util.ChangeFilter(
            category=None, branch_re=git_branch_name),
        hour={{nightly_build_hour}},
        onlyIfChanged=True,
        builderNames=[
            pretty_branch_name + " Debian Packaging",
            pretty_branch_name + " RPM Packaging",
        ])

    triggerable_packaging = schedulers.Triggerable(
        name=pretty_branch_name + ' Packaging Triggerable',
        builderNames=[
            pretty_branch_name + " Debian Packaging",
            pretty_branch_name + " RPM Packaging",
        ])

{% if groups['workers'] | map('extract', hostvars) | selectattr('repo_builder', 'defined') | selectattr('repo_builder') | list | length > 0 or
      groups['workers'] | map('extract', hostvars) | selectattr('only_repo_builder', 'defined') | selectattr('only_repo_builder') | list | length > 0 %}
    triggerable_deb_repo = schedulers.Triggerable(
        name=pretty_branch_name + ' Debian Repo Triggerable',
        builderNames=[
            pretty_branch_name + " Debian Repository"
        ])

    triggerable_rpm_repo = schedulers.Triggerable(
        name=pretty_branch_name + ' RPM Repo Triggerable',
        builderNames=[
            pretty_branch_name + " RPM Repository"
        ])
{% endif %}

    #Note: This is a hack, but we need a unique name for the force schedulers, and it can't have special characters in it...
    forceScheduler = schedulers.ForceScheduler(
        name="ForceBuildCommits" + pretty_branch_name[0],
        buttonName="Force Build",
        label="Force Build Settings",
        builderNames=[
            pretty_branch_name + " Build",
            pretty_branch_name + " Reports",
            pretty_branch_name + " Markdown",
            pretty_branch_name + " Database Tests",
            pretty_branch_name + " Debian Packaging",
            pretty_branch_name + " RPM Packaging",
{% if groups['workers'] | map('extract', hostvars) | selectattr('repo_builder', 'defined') | selectattr('repo_builder') | list | length > 0 or
      groups['workers'] | map('extract', hostvars) | selectattr('only_repo_builder', 'defined') | selectattr('only_repo_builder') | list | length > 0 %}
            pretty_branch_name + " Debian Repository",
            pretty_branch_name + " RPM Repository",
{% endif %}
        ],
        codebases=[
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
        ],

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

    scheduler_list.extend([commits_branch, nightly_branch, triggerable_packaging, forceScheduler])
{% if groups['workers'] | map('extract', hostvars) | selectattr('repo_builder', 'defined') | selectattr('repo_builder') | list | length > 0 or
      groups['workers'] | map('extract', hostvars) | selectattr('only_repo_builder', 'defined') | selectattr('only_repo_builder') | list | length > 0 %}
    scheduler_list.extend([ triggerable_deb_repo, triggerable_rpm_repo ])
{% endif %}
    return scheduler_list
