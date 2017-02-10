#!/usr/bin/python
# -*- coding: utf-8 -*-

import os , re ,etcd , time , json , commands
import logging
from etcd import EtcdKeyNotFound

current_dir = os.path.split(os.path.realpath(__file__))[0]
log = logging.getLogger(__name__)

log.setLevel(logging.DEBUG)

class ContainerEtcd(object):
    def __init__(self , etcd_host="127.0.0.1" , etcd_port = 4001):
        self.etcdCli = etcd.Client(host = etcd_host , port=int(etcd_port))



    def copy(self,src="",dest=""):
        log.info("Copy key[%s]  To key[%s]."%(src,dest))
        try:
            srcDatas = self.etcdCli.get(src)
        except EtcdKeyNotFound:
            log.warning("Src Key[%s] not Exists." % src)
            return
        value = srcDatas.value
        if srcDatas.dir == True:
            for child in srcDatas.children:
                child_src = child.key
                child_dest = os.path.join(dest,child_src.split("/")[-1])
                self.copy(src=child_src , dest = child_dest)
        else:
            self.etcdCli.set(dest , value)
        # log.info("delete key[%s] from etcd."%src)
        # self.etcdCli.delete(src,recursive=True)

    def set_dict_key(self,key="",datas={}):
        log.info("set key[%s] to etcd."%key)
        for k , v in datas.items():
            kk = os.path.join(key , k)
            self.etcdCli.set(kk , v)


    def del_dict_key(self,key="",datas={}):
        log.info("Start Del  From Etcd In Path %s."%key)
        for k , v in datas.items():
            kk = os.path.join(key , k)
            log.info("Del key %s"%kk)
            try:
                self.etcdCli.delete(kk , recursive=True)
            except EtcdKeyNotFound:
                log.warning("Key[%s] not Exists." % kk)
                return


    def get_child(self, key=""):
        """获取当前容器"""
        logging.info("Get Key %s From Etcd." % key)
        try:
            datas = {}
            try:
                parent = self.etcdCli.get(key)
            except EtcdKeyNotFound:
                return datas
            for child in parent.children:
                if child.key == key: continue
                datas[child.key.split('/')[-1]] = child.value
        except Exception, err:
            logging.warning(err)
            datas = {}
        logging.info("Containers : %s" % json.dumps(datas))
        return datas
    
    
class Image():
    def build(self, dockerfile='.'):
        image_tag = self.image_tag_name
        status = True
        logging.info('Start To Build Image %s' % image_tag)
        for msg in self.dockerClient.build(path=dockerfile, tag=image_tag, forcerm=True):
            logging.info(msg)
            if re.search("error", msg, re.IGNORECASE):
                status = False
        if not re.search("Successfully", msg, re.IGNORECASE):
            status = False

        if status == True:
            logging.info("Build Docker Image[SUCCESS].")
        else:
            logging.error("Build Docker Image[FAILD].")
            exit(1)
        return status
    
    def push(self,image_tag_src=None,image_tag_dest=None):
        if image_tag_src == None:image_tag_src= self.image_tag_name
        if image_tag_dest == None:image_tag_dest= self.image_tag_name

        self.dockerClient.tag(image_tag_src , repository=self.registry+"/"+image_tag_dest)
        response = self.dockerClient.push(repository=self.registry+"/"+image_tag_dest)
        if re.search("ERROR",response,re.IGNORECASE):
            log.error("PUSH IMAGE[%s] TO REPOSITORY FAILD."%image_tag_dest)
            log.error(response)
            exit(1)
        else:
            log.info(response)

    def publish(self):
        if self.ks_project_status == "publish":
            log.info("Publish")
        else:
            log.error("Only PM Can Publish Project.")
            exit(1)
        image_tag_src = self.registry+'/'+self.image_tag_name
        image_tag_dest = "%s:PROD-%s"%(self.image,self.tag)
        self.pull()
        self.push(image_tag_src=image_tag_src,image_tag_dest=image_tag_dest)



class Container(ContainerEtcd,Image):
    def __init__(self,base_url="tcp://127.0.0.1:2375" , status="dev" , project = "kop" ,tag="dev",etcd_server="127.0.0.1:4001",registry="127.0.0.1:5000"):
        if re.search("http" , base_url):
            from shipyard import  Client
            import urlparse
            username = urlparse.parse_qs(urlparse.urlparse(base_url).query).get("username",[""])[0]
            password = urlparse.parse_qs(urlparse.urlparse(base_url).query).get("password",[""])[0]
            base_url = urlparse.urlparse(base_url).scheme + "://" + urlparse.urlparse(base_url).netloc
            print username , password , base_url
            self.dockerClient = Client(base_url=base_url , username = username , password = password)
        else:
            from docker import Client
            self.dockerClient = Client(base_url=base_url)

        self.image = project
        self.branch = self.get_project_branch()
        self.ks_project_status = status
        self.tag = self.branch+"."+ tag

        self.image_tag_name = "%s:%s" % (self.image, self.tag)
        self.project = project
        self.base_key = "/{env}/nginx/{project}/".format(project=project, env=status)
        self.etcd_host = etcd_server.split(':')[0]
        self.etcd_port = etcd_server.split(':')[1]
        self.etcdCli = etcd.Client(host=self.etcd_host, port=int(self.etcd_port))
        self.registry = registry


    def get_public_port(self,container):
        try:
            container_network = \
            self.dockerClient.inspect_container(container).get("NetworkSettings", {}).get("Ports", {}).get(
                "8080/tcp", [])[0]
        except Exception, err:
            logging.error("Container %s Port Is Required." % container)
            logging.error(err)
            # container_network = {"HostIp":"127.0.0.1","HostPort":90}
            container_network = {}
            status = False
            return status
        if not isinstance(container_network, dict):
            logging.error("Container Inspect Error, %s" % container_network)
            status = False
            return status
        hostIp = container_network.get('HostIp', None)
        hostPort = container_network.get("HostPort", None)
        if hostIp==None  or hostPort == None:
            return False
        else:
            return "%s:%s"%(hostIp , hostPort)

    def get_project_branch(self):
        branch = commands.getoutput('git branch -a |sort -r | head -n 1 | sed "s/remotes\/origin\///"')
        branch = re.sub('\*','',branch)
        branch = re.sub("/","-",branch)
        branch = branch.strip()
        log.info(branch)
        return branch

    def get_container_ip(self,container,network_mode="ks_overlay"):
        Ports = self.dockerClient.inspect_container(container).get("NetworkSettings", {}).get("Ports",{})
        Networks = self.dockerClient.inspect_container(container).get("NetworkSettings", {}).get("Networks",{}).get(network_mode,{})
        IPAddress = Networks.get("IPAddress",None)
        if "8080/tcp" in Ports.keys() and IPAddress!=None:
            return "%s:%s"%(IPAddress , "8080")
        elif "80/tcp" in Ports.keys() and IPAddress!=None:
            return "%s:%s"%(IPAddress, "80")
        else:
            return None


    def pull(self,image=None,tag=None):
        if tag == None:tag = self.tag
        if image == None:image  = self.image
        log.info("pull image %s:%s from registry %s."%(image , tag , self.registry))
        response = self.dockerClient.pull(self.registry+'/'+image,tag=tag)
        if re.search("ERROR", response, re.IGNORECASE):
            log.error("PULL IMAGE[%s] TO REPOSITORY FAILD." %(image+":"+tag) )
            log.error(response)
            exit(1)
        else:
            log.info(response)

    def create(self,num=1):
        set_key = os.path.join(self.base_key,"waiting")
        log.info("create container ")
        status = True
        image_name =self.registry+"/"+ self.image_tag_name

        datas = {}
        for i in range(num):
            try:
                container = self.dockerClient.create_container(image_name, environment={"KS_SYS_ENV":self.ks_project_status,"KS_PROJECT":self.project},name="%s_%s_%s_%s_%s" % (self.ks_project_status, self.image , self.tag,os.getenv("GO_STAGE_COUNTER") or int(time.time()), i ))
                container_id = container.get('Id', None)
            except Exception, err:
                log.error("Create Container From Image %s [Faild]." % image_name)
                log.error(err)
                status = False
                break
            datas[container_id]=""

        if status == True:
            self.set_dict_key(set_key,datas)
        else:
            log.error("Create Container Faild , Start To Remove......")
            for id , v in datas.items():
                try:
                    self.dockerClient.remove_container(id , force=True)
                except Exception , err:
                    log.error(err)
            exit(1)

    def start(self):
        get_key = os.path.join(self.base_key,"waiting")
        set_key = os.path.join(self.base_key,"online")
        offline_key = os.path.join(self.base_key , "offline")

        datas = self.get_child(key=get_key)
        if len(datas) == 0 :
            log.warning("Can Not Found Any Record In Key %s"%get_key)
            exit(1)
        newdatas = {}
        status = True
        for container_id in datas.keys():
            try:
                self.dockerClient.start(container_id,publish_all_ports=True,network_mode="ks_overlay")
                # network = self.get_public_port(container_id)
                network = self.get_container_ip(container_id, network_mode="ks_overlay")
                newdatas[container_id] = network
            except Exception , err:
                status = False
                log.error("Start Container  %s [Faild]." %container_id )
                log.error(err)





        if status == False:
            log.error("Start Container Faild , Stat To Remove......")
            for container in newdatas.keys():
                try:
                    self.dockerClient.remove_container(container)
                except Exception,err:
                    log.error(err)
            self.etcdCli.delete(get_key , recursive=True)
            exit(1)
        else:
            log.info("Start Container Success , Start Set Network Message To Etcd .....")
            self.copy(set_key , offline_key )

            self.set_dict_key(set_key , newdatas)
            self.del_dict_key(set_key , self.get_child(offline_key))
            self.del_dict_key(get_key , datas)



    def stop(self):
        """stop conatiner search from etcd"""
        get_key = os.path.join(self.base_key , "offline")
        set_key = os.path.join(self.base_key , "invalid")

        datas = self.get_child(get_key)
        if len(datas)==0:
            log.warning("Can Not Found Any Record In Key %s" % get_key)
            return
        for k, v in datas.items():
            try:
                self.dockerClient.stop(k)
            except Exception, err:
                log.error("Stop Container %s Faild." % k)
                log.error(err)

        self.copy(get_key, set_key)
        self.etcdCli.delete(key=get_key, recursive=True)

    def delete(self):
        """delete container search from etcd"""
        get_key = os.path.join(self.base_key, "invalid")
        datas = self.get_child(get_key)
        if len(datas)==0:
            log.warning("Can Not Found Any Record In Key %s" % get_key)
            return
        for k, v in datas.items():
            try:
                self.dockerClient.remove_container(k)
            except Exception, err:
                log.error("Stop Container %s Faild." % k)
                log.error(err)
        self.etcdCli.delete(key=get_key, recursive=True)



def main():
    def __tag__():
        datas = os.environ
        log.debug(str(datas))
        project_name = os.getenv("KS_PROJECT_NAME")
        if project_name!=None:
            project_name = re.sub('-','_',project_name)
        for k, v in datas.items():
            if re.search("GO_DEPENDENCY_LABEL", k,re.IGNORECASE) and project_name!=None and re.search(project_name,k,re.IGNORECASE):
                return v
        return os.getenv("GO_PIPELINE_LABEL")

    import argparse
    parser = argparse.ArgumentParser(description='args')


    subparser = parser.add_subparsers(dest='action')
    action_build = subparser.add_parser("build", help="build image")
    action_push = subparser.add_parser("push", help="push image ti registry")
    action_pull = subparser.add_parser("pull", help="pull image from registry")
    action_create = subparser.add_parser("create", help="create docker container")
    action_start = subparser.add_parser("start", help="start docker container")
    action_stop = subparser.add_parser("stop", help="stop docker container")
    action_delete = subparser.add_parser("delete", help="delete docker container")
    action_publish = subparser.add_parser("publish", help="publish docker image")

    for sp in  [action_build,action_push,action_pull,action_create ,action_start ,action_stop , action_delete,action_publish]:
        sp.add_argument("--docker_server" , help="env.KS_DOCKER_SERVER or docker api or shipyard api" , default=os.getenv("KS_DOCKER_SERVER"),required=False if os.getenv("KS_DOCKER_SERVER") else True )
        sp.add_argument("--etcd" , help="env.KS_ETCD_SERVER or etcd api" , default=os.getenv("KS_ETCD_SERVER"),required=False if os.getenv("KS_ETCD_SERVER") else True)
        sp.add_argument("--status" , help="env.KS_PROJECT_STATUS or env" , default=os.getenv("KS_PROJECT_STATUS"),required=False if os.getenv("KS_PROJECT_STATUS") else True)
        sp.add_argument("--project", help=u"env.KS_PROJECT_NAME : project name", default=os.getenv("KS_PROJECT_NAME"),required=False if os.getenv("KS_PROJECT_NAME") else True)
        sp.add_argument('--tag', help=u"env.GO_PIPELINE_LABEL : image tag", default=__tag__(), required=False)
        sp.add_argument('--registry', help=u"env.KS_DOCKER_REGISTRY : docker  registry", default=os.getenv("KS_DOCKER_REGISTRY"),required=False if os.getenv("KS_DOCKER_REGISTRY") else True)



    action_build.add_argument("--dockerfile",help="the path of dockerfile.",default= '.')
    action_create.add_argument("--containers", help=u"start docker num", default=1, type=int)


    # args = parser.parse_args("create --docker_server http://192.168.17.230:8080?username=admin&password=123456 --etcd 192.168.17.230:14001 --env dev --project centos --tag latest".split(' '))
    # args = parser.parse_args("--docker_server http://192.168.17.230:8080?username=admin&password=123456 --etcd 192.168.17.230:14001 --env dev --project centos start".split(' '))
    # args = parser.parse_args("--docker_server http://192.168.17.230:8080?username=admin&password=123456 --etcd 192.168.17.230:14001 --env dev --project kop-server stop".split(' '))
    # args = parser.parse_args("--docker_server http://192.168.17.230:8080?username=admin&password=123456 --etcd 192.168.17.230:14001 --env dev --project kop-server delete".split(' '))
    # args = parser.parse_args("--docker_server http://192.168.17.230:8080?username=admin&password=123456 --etcd 192.168.17.230:14001 --env dev --project kop-server delete".split(' '))
    # args = parser.parse_args("create --help".split(' '))
    # args = parser.parse_args("--help".split(' '))
    args = parser.parse_args()
    log.info(str(args))
    action = args.action
    myContainer = Container(base_url=args.docker_server , status = args.status , project = args.project ,tag=args.tag, etcd_server = args.etcd , registry=args.registry)
    if action == "build":
        myContainer.build(dockerfile=args.dockerfile)
    elif action == "push":
        myContainer.push()
    elif action == "pull":
        myContainer.pull()
    elif action == "create":
        myContainer.create( num = args.containers)
    elif action == "start":
        myContainer.start()
    elif action == "stop":
        myContainer.stop()
    elif action == "delete":
        myContainer.delete()
    elif action == 'publish':
        myContainer.publish()


if __name__=="__main__":
    logging.basicConfig(level = logging.DEBUG)
    main()
