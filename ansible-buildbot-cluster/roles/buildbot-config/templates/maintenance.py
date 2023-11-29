# -*- python -*-
# ex: set filetype=python:

import os.path
from buildbot.plugins import steps, util, schedulers
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
              return re_fn()
          objects = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Prefix=prefix, ContinuationToken = objects.get("ContinuationToken"))


    def prefix_size(self, s3, prefix):
        def sum_of_sizes(objects):
          nonlocal total
          nonlocal date
          # loop through the objects and add their sizes together, then add it to total
          total += sum([ o['Size'] for o in objects['Contents']])
          date = objects['Contents'][0]['LastModified']

        def summarize():
          nonlocal total
          nonlocal date
          return {'date': date, 'size': total }

        total = 0
        date = 0
        return self.for_all_in_prefix(s3, prefix, sum_of_sizes, summarize)


    def clean_single_build_dir(self, s3, prefix, before_date=None):
        def clean_prefix(objects_to_delete):
            nonlocal prefix
            nonlocal prefix_deleted
            #Check if the stuff in this prefix is *earlier* than the before_date
            #NB: This is assuming that the first key in this prefix *is dated the same as everything else in this prefix*
            excluded_hash = False
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

        def summarize():
                nonlocal prefix_deleted
                nonlocal prefix
                print(f"Deleted a total of { prefix_deleted } files from { prefix }")
                self.deleted += prefix_deleted

        prefix_deleted = 0
        self.for_all_in_prefix(s3, prefix, clean_prefix, summarize)


    def clean_prefix(self, s3, vers, process_whitelist=True, before_date=None):
        print(f"Processing { vers }")
        #NB: We're assuming here that we've never got more than 1k builds present!  Eventually they'd all get processed, but it would take *days*
        vers_dir = s3.list_objects_v2(Bucket="{{ s3_public_bucket }}", Delimiter="/", Prefix=f"builds/{ vers }/")
        candidate_hashes = self.prefixes_to_keys(vers_dir)
        print(f"Found { len(candidate_hashes) } possible hashes to delete")
        try:
            whitelist = s3.get_object(Bucket="{{ s3_public_bucket }}", Key=f"builds/{ vers }/latest.txt")['Body'].read().decode("utf-8").strip()
            whitelist = f"builds/{ vers }/{ whitelist }/"
            if process_whitelist and whitelist in candidate_hashes:
                candidate_hashes.remove(whitelist)
        except ClientError as ex:
            print(f"NoSuchKey for builds/{ vers }/latest.txt, not whitelisting anything for { vers }")
        excluded_hashes = []
        remaining_prefixes = {}
        for hash in candidate_hashes:
            self.clean_single_build_dir(s3, hash, before_date)
            remaining_prefixes[hash] = self.prefix_size(s3, hash)

        if ('Contents' in vers_dir and len(vers_dir['Contents']) == 1 or 'KeyCount' in vers_dir and vers_dir['KeyCount'] == 1) and 'CommonPrefixes' not in vers_dir:
            print(f"Removing latest.txt marker file from { vers }")
            for key in self.contents_to_keys(vers_dir):
                s3.delete_object(Bucket="{{ s3_public_bucket }}", Key=key)
                self.deleted += 1
        return remaining_prefixes


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

        remaining_prefixes = {}
        for vers in SUPPORTED_BRANCHES:
            remaining_prefixes.update(self.clean_prefix(s3, vers, process_whitelist=True, before_date=delete_before))
        total_size = sum([ int(remaining_prefixes[prefix]['size']) for prefix in remaining_prefixes] )
        print(f"Calculated artifacts storage size is { total_size } bytes for { len(remaining_prefixes) } prefixes")

        pruning_list = sorted(remaining_prefixes, key=lambda x: (remaining_prefixes[x]['date'], remaining_prefixes[x]['size']))
        print(f"Total size of { total_size } >= max size of { {{ max_artifacts_size | default(32)}} * 1073741824 }")
        while total_size >= {{ max_artifacts_size | default(32)}} * 1073741824 and len(pruning_list) > 0:
            prefix_to_prune = pruning_list.pop()
            print(f"Pruning { prefix_to_prune } due to size limits")
            self.clean_single_build_dir(s3, prefix_to_prune)
            total_size -= remaining_prefixes[prefix_to_prune]['size']

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


class Maintenance():

    REQUIRED_PARAMS = [
        "git_branch_name",
        "workernames"
        ]

    OPTIONAL_PARAMS = [
        ]

    props = {}

    def __init__(self, props):
        for key in Maintenance.REQUIRED_PARAMS:
            if not key in props:
                pass
                #fail
            if type(props[key]) in [str, list]:
                self.props[key] = props[key]

        for key in Maintenance.OPTIONAL_PARAMS:
            if key in props:
                self.props[key] = props[key]



    def getBuildPipeline(self):
        f_build = util.BuildFactory()
        f_build.addStep(GenerateDeleteCommands(name="Clean S3 host"))

        return f_build


    def getBuilders(self):

        builders = []

        builders.append(util.BuilderConfig(
            name="Opencast Maintenance",
            factory=self.getBuildPipeline(),
            workernames=self.props['workernames']))

        return builders


    def getSchedulers(self):

        scheds = {}
        scheds['maintenance'] = schedulers.Nightly(
            name="Opencast Maintenance",
            hour={{ nightly_build_hour }},
            builderNames=['Opencast Maintenance'] + [ f"ocqa { w } docker cleanup" for w in self.props['workernames'] ])


        scheds['forceMaint'] = schedulers.ForceScheduler(
            name="OpencastMaintenanceForceBuild",
            buttonName="Force Build",
            label="Force Build Settings",
            builderNames=["Opencast Maintenance"],
            codebases=[
                util.CodebaseParameter(
                    "",
                    label="Main repository",
                    # will generate a combo box
                    branch=util.FixedParameter(
                        name="branch",
                        default=self.props['git_branch_name'],
                    ),
                    # will generate nothing in the form, but revision, repository,
                    # and project are needed by buildbot scheduling system so we
                    # need to pass a value ("")
                    revision=util.FixedParameter(name="revision", default="HEAD"),
                    repository=util.FixedParameter(
                        name="repository", default="{{ source_repo_url }}"),
                    project=util.FixedParameter(name="project", default=""),
                ),
            ],

            # will generate a text input
            reason=util.StringParameter(
                name="reason",
                label="Reason:",
                required=False,
                size=80,
                default=""),

            # in case you don't require authentication this will display
            # input for user to type his name
            username=util.UserNameParameter(label="your name:", size=80))

        return scheds
