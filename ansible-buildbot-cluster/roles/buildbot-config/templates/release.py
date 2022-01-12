# -*- python -*-
# ex: set filetype=python:

from twisted.internet import defer
from buildbot.process.results import SUCCESS
from buildbot.plugins import steps, util
from github import Github
import common


class GenerateGithubRelease(steps.BuildStep):

    def __init__(self, release_tag, release_name, release_message, **kwargs):
        super().__init__(**kwargs)
        
        self.tag = release_tag
        self.name = release_name
        self.message = release_message

    #@defer.inlineCallbacks
    def run(self):
        g = Github("{{ github_token }}")

        opencast = g.get_repo("{{ source_pr_owner }}/{{ source_pr_repo }}")

        release = opencast.create_git_release(tag=f"{self.tag}", name=f"{self.name}", message=f"{self.message}", prerelease=True)
        #release.upload_asset(path="./test.txt", content_type="application/txt")
        return SUCCESS

    #@defer.inlineCallbacks
    def getCurrentSummary(self):
        return dict({
                 "step": f"Creating { self.tag } release named { self.name }"
               })

    #@defer.inlineCallbacks
    def getResultSummary(self):
        return dict({
                 "step": f"Created { self.tag } release named { self.name }",
                 "build": f"I dunno lol"
               })


def __getBasePipeline():

    f_build = util.BuildFactory()
    f_build.addStep(common.getPreflightChecks())
    f_build.addStep(common.getClone())
    f_build.addStep(common.setLocale())
    f_build.addStep(common.setTimezone())

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getWorkerPrep())
    #Freak out and throw an exception, this should *not* do anything
    return f_build


def getBuildPipeline():

    github_release = GenerateGithubRelease(
        release_tag=util.Interpolate("%(prop:branch)s"),
        release_name=util.Interpolate("Opencast %(prop:branch)s"),
        release_message=util.Interpolate("Changelog available at #TODO"),
        haltOnFailure=True,
        flunkOnFailure=True)

    f_build = __getBasePipeline()
    f_build.addStep(common.getWorkerPrep())
    f_build.addStep(common.loadMavenSettings())
    f_build.addStep(common.loadSigningKey())
    f_build.addStep(common.getBuild(override=['install', 'nexus-staging:deploy', 'nexus-staging:release', '-P', 'release,none', '-s', 'settings.xml', '-DstagingProgressTimeoutMinutes=10'], timeout=600))
    f_build.addStep(common.unloadSigningKey())
    f_build.addStep(common.getTarballs())
    #f_build.addStep(github_release)
    f_build.addStep(common.unloadMavenSettings())
    f_build.addStep(common.getClean())

    return f_build
