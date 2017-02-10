#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import logging

current_dir = os.path.split(os.path.realpath(__file__))[0]
log = logging.getLogger(__name__)
from gocd import Server
from gocd.api import PipelineConfig
import copy
import commands , json ,re
class KSGOCD():
    def __init__(self,gocdhost,user,password):
        self.server = Server(gocdhost, user=user, password=password)


    def get_project_pipeline(self,pipeline_name='kop-server'):
        branch = commands.getoutput('cd /var/lib/go-agent/pipelines/{name} && git branch -a| grep release |sort -r | head -n 1 | sed "s/remotes\/origin\///"'.format(name=pipeline_name)).strip()
        if branch == None or branch=="":
            log.error("Not Found Any Branch Like release.")
            exit(1)
        branch = re.sub('\*','',branch)
        branch = branch.strip()
        log.info(branch)
        return branch

    def update_git_branch(self,pipeline_name="kop-server",branch=None):
        if branch == None: branch = self.get_project_pipeline(pipeline_name=pipeline_name)
        kop_conf = PipelineConfig(self.server, pipeline_name)
        response = kop_conf.get()
        etag = response.headers.get('ETag', None)
        datas = copy.copy(response.body)
        log.info(json.dumps(datas))
        for material in datas.get("materials", []):
            if material.get('type', None) != 'git':
                continue
            attrs = material.get('attributes', {})
            if 'branch' in attrs.keys():
                attrs['branch'] = branch
        response = kop_conf.edit(datas, etag)
        if not response.is_ok :
            exit(1)
            log.error(response.body)


if __name__=="__main__":
    logging.basicConfig(level = logging.DEBUG)
    import argparse,urlparse

    parser = argparse.ArgumentParser(description='args')

    subparser = parser.add_subparsers(dest='action')
    action_config = subparser.add_parser("config", help="edit config")
    for sp in [action_config]:
        sp.add_argument("--gocdserver", help="env.KS_GOCD_SERVER",default=os.getenv("KS_GOCD_SERVER"),
                        required=False if os.getenv("KS_GOCD_SERVER") else True)

    action_config.add_argument("--pipeline",help="",default=None,required=True)
    action_config.add_argument("--branch",help="env.KS_PROJECT_BRANCH",default=os.getenv("KS_PROJECT_BRANCH"),required=False)

    args = parser.parse_args()
    # args = parser.parse_args( "config --gocdserver http://192.168.1.230:8153?user=admin&password=xxx --pipeline kop-server --branch release".split(' '))

    log.info(str(args))
    action = args.action

    gocdserver = args.gocdserver
    user = urlparse.parse_qs(urlparse.urlparse(gocdserver).query).get("username", [""])[0]
    password = urlparse.parse_qs(urlparse.urlparse(gocdserver).query).get("password", [""])[0]
    base_url = urlparse.urlparse(gocdserver).scheme + "://" + urlparse.urlparse(gocdserver).netloc
    myKSGOCD = KSGOCD(base_url,user,password)
    if action == 'config':

        pipeline  = args.pipeline
        branch = args.branch

        myKSGOCD.update_git_branch(pipeline_name=pipeline , branch=branch)
