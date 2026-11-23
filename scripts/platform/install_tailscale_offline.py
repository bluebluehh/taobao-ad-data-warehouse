#!/usr/bin/env python3
"""Install the already verified local package; do not authenticate a VPN device."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess


def main():
    node = socket.gethostname().split('.')[0]
    if node not in ['adw101', 'adw102', 'adw103']:
        raise SystemExit('只能在三个项目节点上安装')
    if os.geteuid() != 0:
        raise SystemExit('请在本节点使用sudo执行，密码仅在终端输入')
    if Path('/etc/taobao-clone-identity').read_text().strip() != node:
        raise SystemExit('节点身份不符，停止')
    root = Path('/opt/taobao/software/tailscale-offline')
    manifest = json.loads((root/'manifest.json').read_text())
    filename = manifest['file']
    if Path(filename).name != filename or not filename.endswith('_amd64.deb'):
        raise SystemExit('安装文件名不符')
    package = root/filename
    with package.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != manifest['sha256']:
        raise SystemExit('安装包校验失败，停止')
    if subprocess.check_output(['dpkg-deb', '-f', str(package), 'Package'], text=True).strip() != 'tailscale':
        raise SystemExit('软件包名称不符')
    subprocess.run(['dpkg', '--install', str(package)], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'tailscaled'], check=True)
    subprocess.run(['tailscale', 'version'], check=True)
    subprocess.run(['systemctl', 'is-active', 'tailscaled'], check=True)
    print(node+'客户端已安装，尚未执行设备登录。不要在分发前复制已登录的VPN状态。')


if __name__ == '__main__':
    main()
