#!/usr/bin/env python3
"""Replace the fresh node scheduler's initial admin password; never print credentials."""
import json
import os
from pathlib import Path
import secrets
import socket

from scheduler_api import Scheduler


def main():
    if socket.gethostname().split('.')[0] != 'adw101':
        raise SystemExit('仅允许在adw101运行')
    path = Path('/opt/taobao/data/reporting/credentials.json')
    private = json.loads(path.read_text())
    if 'scheduler_admin' in private:
        Scheduler().call('/users/get-user-info')
        print('调度管理员已有独立密码，登录检查通过')
        return
    candidate = private.setdefault('scheduler_admin_pending', secrets.token_hex(8))
    path.write_text(json.dumps(private, indent=2))
    path.chmod(0o600)
    try:
        api = Scheduler(password=candidate)
    except RuntimeError:
        api = Scheduler()
        user = api.call('/users/get-user-info')
        api.call('/users/update', {
            'id': user['id'], 'userName': user['userName'], 'userPassword': candidate,
            'email': user.get('email') or 'admin@localhost.invalid',
            'tenantId': user.get('tenantId', -1), 'state': user.get('state', 1),
            'timeZone': 'Asia/Shanghai',
        }, 'POST')
        api = Scheduler(password=candidate)
    api.call('/users/get-user-info')
    private['scheduler_admin'] = candidate
    private.pop('scheduler_admin_pending', None)
    path.write_text(json.dumps(private, indent=2))
    login = path.parent/'scheduler-login.txt'
    with os.fdopen(os.open(login, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600), 'w') as out:
        out.write('本节点调度器\n地址：http://127.0.0.1:12345/dolphinscheduler/\n用户名：admin\n密码：'+candidate+'\n')
    print('调度管理员已使用独立密码；修改后重新登录通过')


if __name__ == '__main__':
    main()
