#!/usr/bin/env python3
"""Prepare a local standalone scheduler using the NEW persistent MySQL instance."""
import json
import os
from pathlib import Path

BASE=Path('/opt/taobao/data/scheduler')
HOME=Path('/opt/taobao/module/apache-dolphinscheduler-3.3.2-bin')

def main():
    for name in ['conf','tasks','resources','logs']:(BASE/name).mkdir(parents=True,mode=0o700,exist_ok=True)
    secret=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
    props=(HOME/'standalone-server/conf/common.properties').read_text()
    settings={'data.basedir.path':str(BASE/'tasks'),'resource.storage.upload.base.path':str(BASE/'resources'),
              'sudo.enable':'false','development.state':'true'}
    lines=[]
    for line in props.splitlines():
        key=line.split('=',1)[0]
        lines.append(key+'='+settings[key] if key in settings else line)
    target=BASE/'conf/common.properties'
    if not target.exists():target.write_text('\n'.join(lines)+'\n')
    config=BASE/'conf/local-application.yaml'
    if not config.exists():
        text='''spring:
  profiles:
    active: mysql
  jackson:
    time-zone: Asia/Shanghai
  sql:
    init:
      mode: never
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://127.0.0.1:3307/dolphinscheduler_meta?useUnicode=true&characterEncoding=UTF-8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai
    username: scheduler_meta
    password: PASSWORD_VALUE
    hikari:
      maximum-pool-size: 8
      minimum-idle: 2
  quartz:
    properties:
      org.quartz.threadPool.threadCount: 3
master:
  workflow-event-bus-fire-thread-count: 2
  logic-task-config:
    task-executor-thread-count: 2
worker:
  physical-task-config:
    task-executor-thread-size: 2
  tenant-config:
    auto-create-tenant-enabled: false
    default-tenant-enabled: true
api:
  python-gateway:
    enabled: false
server:
  address: 127.0.0.1
  port: 12345
'''.replace('PASSWORD_VALUE',json.dumps(secret['scheduler_meta']))
        with os.fdopen(os.open(config,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:out.write(text)
    print('DolphinScheduler独立配置准备完成：持久MySQL、禁用sudo和自动创建系统用户，API仅本机访问。')

if __name__=='__main__':main()
