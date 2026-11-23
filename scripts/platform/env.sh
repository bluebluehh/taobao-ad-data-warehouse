#!/usr/bin/env bash
# Source this file; credentials stay in the existing machine-local Hive config.
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-8-openjdk-amd64}"
export HADOOP_HOME=/opt/taobao/module/hadoop-3.3.6
export HIVE_HOME=/opt/taobao/module/apache-hive-4.0.1-bin
export TEZ_HOME=/opt/taobao/module/apache-tez-0.10.4-bin
export HADOOP_CONF_DIR="${TAOBAO_HADOOP_CONF_DIR:-$HADOOP_HOME/etc/hadoop}"
export HIVE_CONF_DIR="${TAOBAO_HIVE_CONF_DIR:-$HIVE_HOME/conf}"
project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export TEZ_CONF_DIR="${TAOBAO_TEZ_CONF_DIR:-$project_root/platform/conf}"
export HADOOP_CLASSPATH="$TEZ_CONF_DIR:$TEZ_HOME/*:$TEZ_HOME/lib/*"
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HIVE_HOME/bin:$PATH"
