# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common


def getBuildPipeline():

    masterPrep = steps.MasterShellCommand(
        command=["mkdir", "-p",
                util.Interpolate(os.path.normpath("{{ deployed_rpms }}")),
                util.Interpolate(os.path.normpath("{{ deployed_rpms_symlink_base }}"))
        ],
        name="Prep relevant directories on buildmaster")

    f_package_rpms = util.BuildFactory()
    f_package_rpms.addStep(masterPrep)

    return f_package_rpms
