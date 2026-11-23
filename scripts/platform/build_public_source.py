#!/usr/bin/env python3
"""Build a reviewed code/docs snapshot without reading Git state from the parent repo."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DIRECTORIES = ['docs', 'warehouse', 'sql', 'web', 'scripts', 'tests', 'examples', 'platform']
EXTENSIONS = {'.md','.html','.py','.sql','.xml','.json','.sh','.cmd','.txt','.lock','.css','.js','.cjs','.yaml','.yml','.toml','.ini','.service','.conf'}
SKIP_DIRS = {'.git','__pycache__','.venv','node_modules'}


def main():
    files = [ROOT/n for n in ['README.md','.gitignore','.gitattributes'] if (ROOT/n).is_file()]
    for directory in DIRECTORIES:
        folder = ROOT/directory
        if not folder.exists():
            continue
        for path in folder.rglob('*'):
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink() or SKIP_DIRS.intersection(relative.parts):
                continue
            if path.suffix.lower() not in EXTENSIONS:
                continue
            if path.name.startswith('credentials') or path.name.endswith('-login.txt'):
                continue
            if relative.as_posix() == 'platform/team/nodes.json':
                continue
            if path.stat().st_size > 10*1024*1024:
                raise SystemExit('源文件超过人工复核阈值，停止：'+str(relative))
            files.append(path)
    files = sorted(set(files))
    private_path = Path('/opt/taobao/data/reporting/credentials.json')
    private = json.loads(private_path.read_text()) if private_path.is_file() else {}
    for path in files:
        raw = path.read_bytes()
        raw.decode('utf-8-sig')
        if re.search(rb'(?m)^-----BEGIN [A-Z ]*PRIVATE KEY-----\s*$', raw):
            raise SystemExit('发现私钥内容，停止：'+str(path.relative_to(ROOT)))
        for value in private.values():
            if isinstance(value,str) and len(value) >= 12 and value.encode() in raw:
                raise SystemExit('已知本机凭据出现在源文件，停止：'+str(path.relative_to(ROOT)))
    out = ROOT/'output/delivery'
    out.mkdir(exist_ok=True, parents=True)
    target = out/'github-project-source.zip'
    hashes = {}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = 'project-source/'+path.relative_to(ROOT).as_posix()
            archive.write(path,name)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        archive.writestr('SOURCE_FILES_SHA256.json',json.dumps(hashes,indent=2)+'\n')
        archive.writestr('IMPORT_INSTRUCTIONS.txt',
            '先在GitHub Desktop克隆目标项目仓库到独立目录。\n'
            '将project-source文件夹里面的内容复制到克隆目录，不覆盖或删除.git。\n'
            '在Changes检查文件后提交和Push。不要把project-source外层文件夹嵌套进去。\n'
            '保留远端原有历史，不使用强制推送，不操作旧开发机上级Gitee仓库。\n'
            '具体步骤见project-source/docs/18_data_and_github_collaboration.md。\n'
            '本包仅是代码和进度快照，不含原始数据、虚拟机、密码、数据库或已登录状态。\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,digest in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(sha+'  '+target.name+'\n')
    receipt = {'files':len(files),'bytes':target.stat().st_size,'sha256':sha,
               'known_credentials_scan':'passed','zip_integrity':'passed','git_commit':'not_created','github_push':'not_performed'}
    (out/'github-source-build-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    node_target=out/'sql-v2-vm-update.zip'
    with zipfile.ZipFile(node_target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path,'taobao-ad-warehouse/'+path.relative_to(ROOT).as_posix())
        archive.writestr('先阅读-更新说明.txt',
            '先阅读 taobao-ad-warehouse/docs/20_sql_v2_usage.md。\n'
            '停止项目任务，备份旧代码，把taobao-ad-warehouse中的内容合并到同名项目目录。\n'
            '保留现有output、原始数据和机器私有配置，不重装，不格式化HDFS。\n'
            '三台分别更新源码并做本地测试，仅adw101运行upgrade_sql_v2.py扩展报表结构。\n'
            '本包不含真实CSV、数据库、凭据或虚拟机镜像。\n')
        archive.writestr('SOURCE_FILES_SHA256.json',json.dumps({
            'taobao-ad-warehouse/'+path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files},indent=2)+'\n')
    with zipfile.ZipFile(node_target) as archive:
        assert archive.testzip() is None
        for path in files:
            assert archive.read('taobao-ad-warehouse/'+path.relative_to(ROOT).as_posix()) == path.read_bytes()
    node_sha=hashlib.sha256(node_target.read_bytes()).hexdigest()
    node_target.with_suffix('.zip.sha256').write_text(node_sha+'  '+node_target.name+'\n')
    (out/'sql-v2-update-build-check.json').write_text(json.dumps({
        'files':len(files),'bytes':node_target.stat().st_size,'sha256':node_sha,
        'zip_integrity':'passed','known_credentials_scan':'passed','applied_to_clones':False},indent=2)+'\n')
    print(json.dumps({'github_source':receipt,'vm_update':{'files':len(files),'bytes':node_target.stat().st_size,'sha256':node_sha}}))


if __name__ == '__main__':
    main()
