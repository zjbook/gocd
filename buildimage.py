#!/usr/local/Python/bin/python  
# coding:utf8
import docker   
import sys  
from io import BytesIO
#import json  


DockerClientAddr = "192.168.1.10:2375"
RegistryAddr = "192.168.1.11:5000"
ImageName = sys.argv[1]
ImageTag = '%s-%s'%(sys.argv[2],sys.argv[3])
ImageFullName = '%s:%s-%s'%(sys.argv[1],sys.argv[2],sys.argv[3])
content = ''

##build and push the image
#if "Successfully" in json.loads(response[10])['stream']:
    #    ImageID = json.loads(response[10])['stream'][19:].strip()
    #    print ImageID
    #else:
    #    print "Some errors may occured!"
    #    sys.exit()
try:  
    #for line in open('./Dockerfile','r'):
    #    content = content + line
    #f = BytesIO(content)
    cli_registry = docker.Client(base_url='tcp://'+DockerClientAddr)
    #response=[line for line in cli_registry.build(fileobj=f, rm=True, tag=ImageFullName)]
    #print response
    cli_registry.build(path='./', rm=True, tag=ImageFullName)
    cli_registry.tag(image=ImageFullName,repository="%s/%s"%(RegistryAddr,ImageName),tag=ImageTag)
    cli_registry.push(repository="%s/%s"%(RegistryAddr,ImageName),tag=ImageTag)
    cli_registry.pull(repository="%s/%s"%(RegistryAddr,ImageName),tag=ImageTag)
    cli_registry.remove_image(image="%s/%s"%(RegistryAddr,ImageFullName))
    cli_registry.remove_image(image=ImageFullName)
except Exception,e:  
    print str(e)  
    sys.exit()
