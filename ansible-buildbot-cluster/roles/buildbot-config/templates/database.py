# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util
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
                logname='version'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "create database opencast%(prop:buildnumber)s;" | ' + mysqlString),
                haltOnFailure=False,
                logname='createdb'),
            common.shellArg(
                command=util.Interpolate(
                    mysqlString + ' opencast%(prop:buildnumber)s < docs/scripts/ddl/mysql5.sql'),
                haltOnFailure=False,
                logname='newdb'),
            common.shellArg(
                command=util.Interpolate(
                    'echo "drop database opencast%(prop:buildnumber)s;" | ' + mysqlString),
                haltOnFailure=False,
                logname='dropdb'),
        ],
        workdir="build/",
        name="Test database generation script against " + dbname,
        haltOnFailure=False,
        flunkOnFailure=True,
        doStepIf=lambda step: int(step.getProperty("pkg_major_version")) < 9)


def generateDBUpgradeStep(dbname, dbport):

    mysqlString = "mysql -u root -h 127.0.0.1 -P " + dbport

    return common.shellSequence(
        commands=[
            common.shellArg(
                command='bash docs/upgrade/.test.sh ' + dbport,
                haltOnFailure=False,
                logname=dbname),
        ],
        workdir="build/",
        name="Test database upgrade scripts against " + dbname,
        haltOnFailure=False,
        flunkOnFailure=True)


def __getBasePipeline():

    f_build = util.BuildFactory()
    f_build.addStep(common.getClone())
    f_build.addStep(generateDBTestStep("maria", "3307"))
    f_build.addStep(generateDBUpgradeStep("maria", "3307"))
    f_build.addStep(generateDBTestStep("mysql5.6", "3308"))
    f_build.addStep(generateDBUpgradeStep("mysql5.6", "3308"))
    f_build.addStep(generateDBTestStep("mysql5.7", "3309"))
    f_build.addStep(generateDBUpgradeStep("mysql5.7", "3309"))
    f_build.addStep(common.getClean())

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()

    return f_build


def getBuildPipeline():

    f_build = __getBasePipeline()

    return f_build
