# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import steps, util, schedulers
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
from debs import Debs
from rpms import Rpms
import common
import json
import random

class Packages():


    REQUIRED_PARAMS = [
        "git_branch_name",
        "pkg_major_version",
        "branch_pretty",
        "el",
        "Build",
        "workernames"
        ]

    OPTIONAL_PARAMS = [
        ]

    props = {}
    rpms = None
    debs = None
    builders = None
    build_sched = None

    #This is a wrapper around both the debs and rpms because BB Dependent schedulers only support one upstream
    def __init__(self, props):
        for key in Packages.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if "Build" == key:
                self.build_sched = props[key]
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Packages.OPTIONAL_PARAMS:
            if key in props and type(props[key]) in [str, list]:
                self.props[key] = props[key]

        self.pretty_branch_name = self.props["branch_pretty"]
        self.debs = Debs(props)
        self.rpms = Rpms(props)

    def getBuilders(self):

        if not self.builders:
            self.builders = self.debs.getBuilders() + self.rpms.getBuilders()

        return self.builders

    def getSchedulers(self):

        builders = [ builder.name for builder in self.getBuilders() ]

        scheds = {}

        if None == self.build_sched:
            scheds[f"{ self.pretty_branch_name }Packages"] = schedulers.Nightly(
                name=self.pretty_branch_name + ' Package Generation',
                change_filter=util.ChangeFilter(category=None, branch_re=self.props['git_branch_name']),
                hour={{ nightly_build_hour }},
                onlyIfChanged=True,
                properties=self.props,
                builderNames=builders)
        else:
            scheds[f"{ self.pretty_branch_name }Packages"] = schedulers.Dependent(
                name=self.pretty_branch_name + " Packaging Generation",
                upstream=self.build_sched,
                properties=self.props,
                builderNames=builders)

        scheds[f"{ self.pretty_branch_name }PackagesForce"] = common.getForceScheduler(
            props=self.props,
            build_type="Packages",
            builderNames=builders)

        return scheds
