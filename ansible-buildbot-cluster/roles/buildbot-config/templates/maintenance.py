# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import steps, util
from buildbot.process import buildstep, logobserver
from twisted.internet import defer
from buildbot.process.results import SUCCESS
import common
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime, timedelta


class GenerateDeleteCommands(steps.BuildStep):

    def contents_to_keys(self, contents):
        return [ x['Key'] for x in contents['Contents'] ]

    def prefixes_to_keys(self, prefixes):
        if "CommonPrefixes" in prefixes:
          return [ x['Prefix'] for x in prefixes['CommonPrefixes'] ]
        return []

    def for_all_in_prefix(self, s3, prefix, fn, re_fn):
        objects = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Prefix=prefix)
        while 'Contents' in objects and len(objects['Contents']) > 0:
          fn(objects)

          if not objects.get('Truncated'):
              return re_fn(objects)
          objects = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Prefix=prefix, ContinuationToken = objects.get("ContinuationToken"))


    def prefix_size(self, s3, prefix):
        total = 0

        for object in s3.Bucket("{{ s3_public_bucket }}").objects.filter(Prefix=prefix):
            total = total + obj.size
        return total


    def clean_single_build_dir(self, s3, prefix, before_date=None):
        def delete_keys(objects_to_delete):
            #Check if the stuff in this prefix is *earlier* than the before_date
            #NB: This is assuming that the first key in this prefix *is dated the same as everything else in this prefix*
            if before_date is not None and before_date <= objects_to_delete['Contents'][0]['LastModified'].replace(tzinfo=None):
                #Exclude the whole prefix from further consideration
                excluded_hash = True

            if not excluded_hash:
                delete_keys = {'Objects' : []}
                delete_keys['Objects'] = [{'Key' : k} for k in [obj['Key'] for obj in objects_to_delete.get('Contents', [])]]

                print(f"Removing { len(delete_keys['Objects']) } files from { prefix }")
                prefix_deleted += len(delete_keys['Objects'])
                #Actually delete things
                s3.delete_objects(Bucket="{{ s3_public_bucket }}", Delete=delete_keys)
            else:
                print(f"No keys to delete for prefix { prefix }")

        def summarize(ignored):
                print(f"Deleted a total of { prefix_deleted } files from { prefix }")
                self.deleted += prefix_deleted

        prefix_deleted = 0
        self.for_all_in_prefix(s3, prefix, delete_keys, summarize)


    def clean_prefix(self, s3, vers, process_whitelist=True, before_date=None):
        print(f"Processing { vers }")
        #NB: We're assuming here that we've never got more than 1k builds present!  Eventually they'd all get processed, but it would take *days*
        vers_dir = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Delimiter="/", Prefix=f"builds/{ vers }/")
        candidate_hashes = self.prefixes_to_keys(vers_dir)
        print(f"Found { len(candidate_hashes) } possible hashes to delete")
        try:
            whitelist = s3.get_object(Bucket="{{ s3_public_bucket }}", Key=f"builds/{ vers }/latest.txt")['Body'].read().decode("utf-8").strip()
            whitelist = f"builds/{ vers }/{ whitelist }/"
            if process_whitelist:
                candidate_hashes.remove(whitelist)
        except ClientError as ex:
            print(f"NoSuchKey for builds/{ vers }/latest.txt, not whitelisting anything for { vers }")
        excluded_hashes = []
        for hash in candidate_hashes:
            self.clean_single_build_dir(s3, hash, before_date)

        if ('Contents' in vers_dir and len(vers_dir['Contents']) == 1) or ('KeyCount' in vers_dir and vers_dir['KeyCount'] == 1):
            print("Removing latest.txt marker file")
            for key in self.contents_to_keys(vers_dir):
                s3.delete_object(Bucket="{{ s3_public_bucket }}", Key=key)
                self.deleted += 1


    def run(self):
        self.deleted = 0
        SUPPORTED_BRANCHES = [ {% for branch in opencast %}'{{ branch }}', {% endfor %} ]

        # Retrieve the list of existing buckets
        session = boto3.Session()
        s3 = session.client('s3',
            aws_access_key_id='{{ public_s3_access_key }}',
            aws_secret_access_key='{{ public_s3_secret_key }}',
            endpoint_url="{{ s3_host }}")

        build_branches = self.prefixes_to_keys(s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Delimiter="/", Prefix="builds/"))
        for branch in build_branches:
            print(f"Checking if { branch } is still supported")
            branch_name = branch.split('/')[1]
            if branch_name in SUPPORTED_BRANCHES:
                print(f"{ branch } is still supported")
                continue
            print(f"{ branch } is NOT supported")
            self.clean_prefix(s3, branch_name, process_whitelist=False)

        delete_before = datetime.utcnow() - timedelta(days={{ keep_artifacts }})

        for vers in SUPPORTED_BRANCHES: 
            self.clean_prefix(s3, vers, process_whitelist=True, before_date=delete_before)
        return SUCCESS


    def getCurrentSummary(self):
        return dict({
                 "step": "Cleaning S3 host: In Progress",
                 "build": f"Removed { self.deleted } files"
               })


    def getResultSummary(self):
        return dict({
                 "step": "Cleaning S3 host: Done",
                 "build": f"Removed { self.deleted } files"
               })



def __getBasePipeline():

    f_build = util.BuildFactory()

    return f_build


def getPullRequestPipeline():

    f_build = __getBasePipeline()

    return f_build


def getBuildPipeline():


    f_build = __getBasePipeline()
    f_build.addStep(GenerateDeleteCommands(name="Clean S3 host"))

    return f_build
