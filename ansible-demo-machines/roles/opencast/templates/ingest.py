#!/usr/bin/env python3
import yaml
import json
import requests
from requests.auth import HTTPBasicAuth

config = {}


def print_status(ok, title):
    color = '\033[92m' if ok else '\033[91m'
    text = ' ok ' if ok else 'fail'
    print(f'  [{color}{text}\033[0m]: {title}')


def post(path, **kwargs):
    auth = HTTPBasicAuth(
            config['server']['username'],
            config['server']['password'])
    server = config['server']['url']
    return requests.post(f'{server}{path}', auth=auth, **kwargs)


def load_config():
    global config
    with open('media.yml', 'r') as f:
        config = yaml.safe_load(f)


def acl():
    return json.dumps({'acl': {'ace': config['acl']}})


def create_series():
    print('Creating series…')
    for series in config.get('series', []):
        series['acl'] = acl()
        r = post('/series/', data=series)
        ethterms = []
        for ethfield in [f for f in series if f in ("advertised", "subtype", "episodes", "vpUrl1", "vpUrl2", "mmpUrlOld1", "mmpUrlOld2", "doiPrefix", "doiId", "department", "shis", "reverseOrder", "vvz", "semester", "notesSeries", "urlSeries", "legacySeriesId")]:
            ethterms += [{'id': ethfield, 'value': series[ethfield]}]
        auth = HTTPBasicAuth(
                config['server']['username'],
                config['server']['password'])
        server = config['server']['url']
        if len(ethterms) > 0:
            print({'metadata': json.dumps(ethterms)})
            ext = requests.put(f'{server}/api/series/{series["identifier"]}/metadata?type=ethterms/series', auth=auth, data={'metadata': json.dumps(ethterms)})
            print_status(r.ok and ext.ok, series["title"])
        else:
            print_status(r.ok, series["title"])


def create_episodes():
    print('Ingesting episodes…')
    for media in config.get('media', []):
        fields = [('acl', (None, acl()))]
        for field in media:
            for key, value in field.items():
                fields.append((key, (None, value)))
        endpoint = '/ingest/addMediaPackage/' + config['server']['workflow']
        r = post(endpoint, files=fields)
        title = [x[1][1] for x in fields if x[0] == "title"][0]
        print_status(r.ok, title)


if __name__ == '__main__':
    load_config()
    create_series()
    create_episodes()
