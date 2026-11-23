#!/usr/bin/env bash
# Read-only inspection. Run inside the intended Linux host; installs nothing.
set -u
section() { printf '\n## %s\n' "$1"; }
section 'Time and operating system'
date -Is
cat /etc/os-release
uname -a
section 'CPU memory and disk'
getconf _NPROCESSORS_ONLN
free -h
df -hT
section 'Network addresses'
hostname
hostname -I
section 'Installed commands'
for tool in java python3 mysql hadoop hdfs yarn hive beeline spark-submit docker; do
  command -v "$tool" || true
done
section 'Java and Python versions'
java -version 2>&1 || true
python3 --version 2>&1 || true
section 'Existing service ports'
ss -ltn | head -60
section 'Installation directories'
ls -ld /opt /opt/module /opt/software /data 2>/dev/null || true
section 'Official download host resolution'
for host in archive.apache.org downloads.apache.org repo.maven.apache.org pypi.org; do
  getent ahostsv4 "$host" | head -1 || true
done
