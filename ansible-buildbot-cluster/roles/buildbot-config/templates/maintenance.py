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
from datetime import datetime, timedelta


class GenerateDeleteCommands(steps.BuildStep):

    def contents_to_keys(self, contents):
        return [ x['Key'] for x in contents['Contents'] ]

    def prefixes_to_keys(self, prefixes):
        if "CommonPrefixes" in prefixes:
          return [ x['Prefix'] for x in prefixes['CommonPrefixes'] ]
        return []

    def clean_prefix(self, s3, vers, process_whitelist=True, before_date=None):
        print(f"Processing { vers }")
        vers_dir = s3.list_objects_v2(Bucket="public", Delimiter="/", Prefix=f"builds/{ vers }/")
        candidate_hashes = self.prefixes_to_keys(vers_dir)
        print(f"Found { len(candidate_hashes) } possible hashes to delete")
        whitelist = s3.get_object(Bucket="public", Key=f"builds/{ vers }/latest.txt")['Body'].read().decode("utf-8").strip()
        whitelist = f"builds/{ vers }/{ whitelist }/"
        if process_whitelist:
          candidate_hashes.remove(whitelist)
        excluded_hashes = []
        for hash in candidate_hashes:
            #Find the first 1k results prefixed by the hash
            objects_to_delete = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Prefix=hash)
            while True:
                #Check if the stuff in this prefix is *earlier* than the before_date
                if before_date is not None and before_date <= objects_to_delete['Contents'][0]['LastModified'].replace(tzinfo=None):
                    #Exclude the whole prefix from further consideration
                    excluded_hashes.append(hash)

                #Figure out what should be deleted
                delete_keys = {'Objects' : []}
                if before_date is not None:
                    delete_keys['Objects'] = [{'Key' : k} for k in filter(lambda obj: "/".join(obj.split('/')[:3]) + "/" not in excluded_hashes, [obj['Key'] for obj in objects_to_delete.get('Contents', [])])]
                else:
                    delete_keys['Objects'] = [{'Key' : k} for k in [obj['Key'] for obj in objects_to_delete.get('Contents', [])]]
      
                if len(delete_keys['Objects']) == 0:
                    print("No keys to delete")
                else:
                    print(f"Removing { len(delete_keys['Objects']) } files")
                    self.deleted += len(delete_keys['Objects'])
                    #Actually delete things
                    s3.delete_objects(Bucket="public", Delete=delete_keys)

                #Are there more results after this?
                if not objects_to_delete.get('Truncated'):
                    break
                objects_to_delete = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Prefix=hash, ContinuationToken = objects_to_delete.get("ContinuationToken"))

        #NB: We use KeyCount here because for a normal, supported OC version the size of 'Contents' is *still* 1 since the directories are *prefixes*
        #    If you screw this up it deletes the whole version tree instead :D
        if vers_dir['KeyCount'] == 1:
            print("Removing latest.txt marker file")
            for key in self.contents_to_keys(vers_dir):
                s3.delete_object(Bucket="public", Key=key)
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
