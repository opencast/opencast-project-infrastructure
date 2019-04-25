
# -*- python -*-
# ex: set filetype=python:

#Assume the keys and repo are mounted somewhere accessible
#TODO:
#    Create the directory structure
#    (re)place files in said structure
#    run createrepo at the top level of the repo
#    done

import os.path
from buildbot.plugins import *
import common


def getBuildPipeline():

    f_repo_rpms = util.BuildFactory()

    return f_repo_rpms
