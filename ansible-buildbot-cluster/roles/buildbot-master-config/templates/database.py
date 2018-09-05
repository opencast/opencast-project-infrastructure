# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common


def generateDBTestStep(dbname, dbport):

    mysqlString = "mysql -u root -h 127.0.0.1 -P " + dbport

    return steps.ShellSequence(
        commands=[
            util.ShellArg(
                command='echo "select version()" | ' + mysqlString,
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='version'),
            util.ShellArg(
                command=util.Interpolate('echo "create database opencast%(prop:buildnumber)s;" | ' + mysqlString),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='createdb'),
            util.ShellArg(
                command=util.Interpolate(mysqlString + ' opencast%(prop:buildnumber)s < docs/scripts/ddl/mysql5.sql'),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='newdb'),
            util.ShellArg(
                command='bash docs/upgrade/.test.sh ' + dbport,
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile=dbname),
            util.ShellArg(
                command=util.Interpolate('echo "drop database opencast%(prop:buildnumber)s;" | ' + mysqlString),
                flunkOnFailure=True,
                haltOnFailure=False,
                logfile='dropdb'),
        ],
        workdir="build/",
        name="Test database and migration scripts against " + dbname,
        haltOnFailure=False,
        flunkOnFailure=True)

def __getBasePipeline(): 

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(generateDBTestStep("maria", "3307"))
    f_build.addStep(generateDBTestStep("mysql5.6", "3308"))
    f_build.addStep(generateDBTestStep("mysql5.7", "3309"))

    return f_build

def getPullRequestPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build

def getBuildPipeline():

    f_build = __getBasePipeline()
    f_build.addStep(common.getClean())

    return f_build
