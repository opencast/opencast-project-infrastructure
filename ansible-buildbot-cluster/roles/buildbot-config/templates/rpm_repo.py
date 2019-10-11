# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util
import common


def getBuildPipeline():

    repo_prep = common.shellCommand(
        command=[
            'mkdir', '-p',
            util.Interpolate('%(prop:rpm_repo_fragment)s/unstable/el/7/noarch/%(prop:pkg_major_version)s/')
        ],
        name='Prep repository structure')

    repo_fetch = common.syncAWS(
        pathFrom="s3://public/builds/{{ rpms_fragment }}",
        pathTo="%(prop:rpm_repo_fragment)s/unstable/el/7/noarch/%(prop:pkg_major_version)s/",
        name='Fetch packages')

    repo_build = common.shellCommand(
        command=[
            'createrepo', '.'
        ],
        workdir=util.Interpolate(
            '%(prop:rpm_repo_fragment)s/unstable/el/7/noarch'),
        name='Build repository')

    f_rpm_repo = util.BuildFactory()
    f_rpm_repo.addStep(common.getPreflightChecks())
    f_rpm_repo.addStep(repo_prep)
    f_rpm_repo.addStep(repo_fetch)
    f_rpm_repo.addStep(common.loadSigningKey())
    f_rpm_repo.addStep(repo_build)
    f_rpm_repo.addStep(common.unloadSigningKey())

    return f_rpm_repo
