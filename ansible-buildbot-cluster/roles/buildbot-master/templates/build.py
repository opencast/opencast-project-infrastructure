# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import common


def getBuildPipeline(branchname, branchInfo):

    checkout = common.getClone(branchname, branchInfo)

    prep = steps.ShellSequence(
        commands=[
            util.ShellArg(command=['git', 'clean', '-fdx'], logfile='clean'),
            util.ShellArg(
                command=[
                    'mvn', '-B', '-V', '-Dmaven.repo.local=./.m2',
                    '-Dmaven.repo.remote=http://{{ inventory_hostname }}/nexus',
                    'dependency:go-offline', '-fn'
                ],
                logfile='deps')
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build Prep")

    build = steps.ShellCommand(
        command=[
            'mvn', '-B', '-V', '-Dmaven.repo.local=./.m2',
            '-Dmaven.repo.remote=http://{{ inventory_hostname }}/nexus',
            'clean', 'install'
        ],
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Build")

    prep_master = steps.MasterShellCommand(
        command=[
            'mkdir', '-p',
            util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}")),
            util.Interpolate(
                os.path.normpath("{{ artifacts_dist_base }}/reports")),
            util.Interpolate(
                os.path.normpath("{{ artifacts_dist_base }}/debs")),
            util.Interpolate(
                os.path.normpath("{{ artifacts_dist_base }}/rpms")),
            util.Interpolate(
                os.path.normpath("{{ deployed_reports_symlink_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

    fix_owner = steps.MasterShellCommand(
        command=[
            'chown', '-R',
            '{{ getent_passwd["buildbot"][1] }}:{{ getent_passwd["buildbot"][2] }}',
            util.Interpolate(os.path.normpath("{{ artifacts_dist_base }}"))
        ],
        name="Fixing ownership of directories we just created")

    #Note: We're using a string here because using the array disables shell globbing!  This applies to the scp steps as well.
    uploadTarballs = steps.ShellCommand(
        command=util.Interpolate(
            "scp build/*.tar.gz {{ buildbot_scp_builds_put }}"),
        haltOnFailure=True,
        flunkOnFailure=True,
        name="Upload build to buildmaster")

    clean = common.getClean()

    f_build = util.BuildFactory()
    #This is needed because the nightly schedulers don't set the branch name for some reason...
    f_build.addStep(
        steps.SetProperty(
            property="branch",
            value=branches[branchname]['branch'],
            name="Set regular branch name"))
    f_build.addStep(
        steps.SetProperty(
            property="branch_pretty",
            value=branchname,
            name="Set pretty branch name"))
    f_build.addStep(
        steps.SetPropertyFromCommand(
            command="date -u +%FT%H-%M-%S",
            property="build_timestamp",
            flunkOnFailure=True,
            warnOnFailure=True,
            haltOnFailure=True,
            name="Get build timestamp"))
    f_build.addStep(checkout)
    f_build.addStep(prep)
    f_build.addStep(build)
    f_build.addStep(prep_master)
    f_build.addStep(fix_owner)
    f_build.addStep(uploadTarballs)
    f_build.addStep(clean)
