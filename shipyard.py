#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import logging

current_dir = os.path.split(os.path.realpath(__file__))[0]


import json,six
from docker import constants
from docker import Client
from docker.utils.decorators import  update_headers





class Client(Client):

    def __init__(self, base_url=None, version=None,
                 timeout=constants.DEFAULT_TIMEOUT_SECONDS, tls=False,
                 user_agent=constants.DEFAULT_USER_AGENT,username=None,password=None):
        super(Client, self).__init__()
        auth_token = self.auth_login( base_url,username, password)
        self.headers['X-Access-Token'] = auth_token
        self.base_url = base_url


    def auth_login(self,base_url='',username="",password=""):
        u = base_url + "/auth/login"
        print u
        res = self._post_json(
            u,
            data={"username":username,"password":password}
        )
        self._raise_for_status(res)
        text = res.text
        auth_token = json.loads(text).get('auth_token', None)
        return "%s:%s"%(username,auth_token)
    def _url(self, pathfmt, *args, **kwargs):
        for arg in args:
            if not isinstance(arg, six.string_types):
                raise ValueError(
                    'Expected a string but found {0} ({1}) '
                    'instead'.format(arg, type(arg))
                )

        args = map(six.moves.urllib.parse.quote_plus, args)

        return '{0}{1}'.format(self.base_url, pathfmt.format(*args))


    @update_headers
    def _post(self, url, **kwargs):
        print "url --- ", url
        if 'headers' in kwargs.keys(): kwargs['headers'].update(self.headers)
        else:kwargs['headers'] = self.headers
        print self._set_request_timeout(kwargs)
        return self.post(url, **self._set_request_timeout(kwargs))

    @update_headers
    def _get(self, url, **kwargs):
        # if 'headers' in kwargs.keys(): kwargs['headers'].update(self.headers)
        # else:kwargs['headers'] = self.headers
        print kwargs
        return self.get(url, **self._set_request_timeout(kwargs))

    @update_headers
    def _put(self, url, **kwargs):
        if 'headers' in kwargs.keys(): kwargs['headers'].update(self.headers)
        else:kwargs['headers'] = self.headers
        return self.put(url, **self._set_request_timeout(kwargs))

    @update_headers
    def _delete(self, url, **kwargs):
        if 'headers' in kwargs.keys(): kwargs['headers'].update(self.headers)
        else:kwargs['headers'] = self.headers
        return self.delete(url, **self._set_request_timeout(kwargs))

if __name__=="__main__":
    # myClient = Client(base_url="http://127.0.0.1:8080",username="admin",password="shipyard")

    myClient = Client(base_url="http://192.168.1.230:8080",username="admin",password="xxxxxxx")
    # print myClient._url("/images")
    # print myClient.images()
    # print myClient.containers()
    # print myClient.stop("8018ecd8ed79")
    # print myClient.start("8018ecd8ed79")
    print "-------ok-------"
    for i in range(1):
        id =  myClient.create_container("centos").get("Id")
        print id
        myClient.start(id)
