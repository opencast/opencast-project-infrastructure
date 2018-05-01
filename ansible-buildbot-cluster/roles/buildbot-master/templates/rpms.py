# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import common


def getBuildPipeline():

    f_package_rpms = util.BuildFactory()

    return f_package_rpms
