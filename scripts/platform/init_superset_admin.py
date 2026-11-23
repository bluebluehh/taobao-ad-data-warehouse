#!/usr/bin/env python3
import json
from pathlib import Path
from superset.app import create_app
from superset.extensions import appbuilder

app=create_app()
with app.app_context():
    sm=appbuilder.sm
    if sm.find_user(username='admin'):
        print('Superset本地管理员已存在，保留账号。')
    else:
        private=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
        user=sm.add_user(username='admin',first_name='本地',last_name='管理员',
            email='admin@localhost.invalid',role=sm.find_role('Admin'),password=private['superset_admin'])
        if not user:raise SystemExit('Superset管理员创建失败')
        print('Superset本地管理员已创建，密码保存在机器私有凭据文件。')
