#!/usr/local/Python/bin/python  
# -*- coding: utf-8 -*-
import etcd
import commands
import sys
defaultencoding = 'utf-8'
if sys.getdefaultencoding() != defaultencoding:
    reload(sys)
    sys.setdefaultencoding(defaultencoding)

       
def etcd_get(etcd_host,etcd_port,project_name,stage_name):
    client = etcd.Client(host=etcd_host, port=etcd_port)    
    try:
        db_version = client.read('/%s/%s'%(project_name,stage_name)).value
        return db_version
    except etcd.EtcdKeyNotFound:
        print "the key not found,or some error occured!"
        return False
        
   
def etcd_write(etcd_host,etcd_port,project_name,stage_name,db_version):
    client = etcd.Client(host=etcd_host, port=etcd_port)
    try:
        client.write('/%s/%s'%(project_name,stage_name), db_version)
        return True
    except Exception,e:
        print "etcd write keys error:",e
        return False

    
def del_sql(file_path,db_version):
    fileobj = open(file_path,'r')
    position = ''
    done = 0
    db_version_new = False
    try:
        while not done:
            line = fileobj.readline()
            if line != '':
                if '--'+db_version+'-end' == line.strip():
                    position = fileobj.tell()
                    print "find position:%s"%(position)
                    break
            else:
                done = 1
        if position == '':
            print "can not find db_version:%s" %(db_version)
            return False 
        else:
            fileobj.seek(position,0)
            sql = fileobj.readlines()
            print len(sql),sql
            if len(sql) == 0:
                print "there is no new sql to excute!!!"
                sys.exit()
            try:
                fileobj2 = open(file_path,'w+')
                for line in sql:
                    if len(line.strip()) == 0:
                        continue
                    if '--' in line.strip():
                        db_version_new = line[2:-5]
                        continue
                    print line
                    fileobj2.write(u'%s'%(line))
                if db_version_new is False:
                    print "there is no new sql to excute!!!"
                    sys.exit()
                else:
                    return db_version_new
            finally:
                fileobj2.close()
    finally:
        fileobj.close()         
        
if __name__ == '__main__':
    file_path = './db.iterations.sql'
    etcd_host = "192.168.17.230"
    etcd_port = 4001
    project_name = sys.argv[1]
    stage_name = sys.argv[2]
    dblist = ['xxx','xxx2']
    if project_name not in dblist:
        print "请指定正确的项目名称，目前支持项目包括：'xxx','xxx2'"
        sys.exit()
    if stage_name == 'dev':
        db_host = '192.168.17.230'
        db_port = 3306
    elif stage_name == 'qa':
        db_host = '192.168.17.231'
        db_port = 3306
    elif stage_name == 'prod':
        pass
    else:
        print '请指明正确的阶段名称，支持三种阶段：dev,qa,prod'
        sys.exit()
    db_name = project_name + '_' + stage_name
    db_user = project_name + '_user'
    db_password = 'kashuo_' + project_name + '_password'
    
    db_version = etcd_get(etcd_host, etcd_port, project_name, stage_name)
    if '20' in db_version:
        db_version_new = del_sql(file_path, db_version) 
        if db_version_new != False:
            (status, output) = commands.getstatusoutput('mysql -u%s -p%s -h%s -P%s %s < %s' %(db_user,db_password,db_host,db_port,db_name,file_path))            
            if status == 0:
                etcd_write_result = etcd_write(etcd_host, etcd_port, project_name, stage_name, db_version_new)
                if etcd_write_result == True:
                    print "the mysql database and etcd have beed updated successfully!"
                else:
                    print "some error occured during etcd_write function execution!"
                    sys.exit()
            else:
                print "some error occured during mysql query execution:%s"%(output)
        else:
            print "some error occured during del_sql function execution!"
            sys.exit()
    else:
        sys.exit()
