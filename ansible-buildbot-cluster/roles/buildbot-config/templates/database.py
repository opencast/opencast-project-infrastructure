# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import *
import common

db_lock = util.WorkerLock("db_lock",
                             maxCount=1)

def generateDBTestStep(dbname, dbport):

    mysqlString = "mysql -u root -h 127.0.0.1 -P " + dbport

    return common.shellSequence(
        commands=[
            common.shellArg(
                command='echo "select version()" | ' + mysqlString,
                haltOnFailure=False,
                logfile='version'),
            common.shellArg(
                command=util.Interpolate('echo "create database opencast%(prop:buildnumber)s;" | ' + mysqlString),
                haltOnFailure=False,
                logfile='createdb'),
            common.shellArg(
                command=util.Interpolate(mysqlString + ' opencast%(prop:buildnumber)s < docs/scripts/ddl/mysql5.sql'),
                haltOnFailure=False,
                logfile='newdb'),
            common.shellArg(
                command='bash docs/upgrade/.test.sh ' + dbport,
                haltOnFailure=False,
                logfile=dbname),
            common.shellArg(
                command=util.Interpolate('echo "drop database opencast%(prop:buildnumber)s;" | ' + mysqlString),
                haltOnFailure=False,
                logfile='dropdb'),
        ],
        workdir="build/",
        name="Test database scripts against " + dbname,
        haltOnFailure=False,
        flunkOnFailure=True)


def __getBasePipeline(): 

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(generateDBTestStep("maria", "3307"))
    f_build.addStep(generateDBTestStep("mysql5.6", "3308"))
    f_build.addStep(generateDBTestStep("mysql5.7", "3309"))
    f_build.addStep(common.getClean())

    return f_build

def getPullRequestPipeline():

    f_build = __getBasePipeline()

    return f_build

def getBuildPipeline():

    f_build = __getBasePipeline()

    return f_build
