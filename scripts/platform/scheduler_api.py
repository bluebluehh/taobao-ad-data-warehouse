#!/usr/bin/env python3
"""Local DolphinScheduler API client. Does not print or persist session tokens in project logs."""
import http.cookiejar
import json
from pathlib import Path
import urllib.parse
import urllib.request

BASE='http://127.0.0.1:12345/dolphinscheduler'
class Scheduler:
    def __init__(self, password=None):
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        private=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
        if password is None:password=private.get('scheduler_admin','dolphinscheduler123')
        result=self.call('/login',{'userName':'admin','userPassword':password},'POST',authenticated=False)
        session=result.get('sessionId')
        if session:self.opener.addheaders.append(('sessionId',session))
    def call(self,path,params=None,method='GET',authenticated=True):
        encoded=urllib.parse.urlencode(params or {}).encode()
        url=BASE+path
        if method=='GET' and encoded:url+='?'+encoded.decode()
        request=urllib.request.Request(url,data=encoded if method!='GET' else None,method=method)
        with self.opener.open(request,timeout=40) as response:result=json.load(response)
        if result.get('code')!=0:raise RuntimeError(f'Scheduler {path}: {result.get("code")} {result.get("msg")}')
        return result.get('data')
