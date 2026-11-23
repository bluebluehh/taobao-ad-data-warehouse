#!/usr/bin/env bash
set -euo pipefail
report_base=/opt/taobao/data/reporting
mysql_prefix=/opt/taobao/module/mysql-ubuntu-8.0.46/usr
export LD_LIBRARY_PATH="$mysql_prefix/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
case "${1:-status}" in
 start)
  test -f "$report_base/mysql-data/auto.cnf"
  if [[ -S "$report_base/mysql.sock" ]] && mysqladmin --no-defaults --socket="$report_base/mysql.sock" ping >/dev/null 2>&1; then
   echo '独立MySQL实例已响应';exit 0
  fi
  exec "$mysql_prefix/sbin/mysqld" --defaults-file="$report_base/mysql.cnf"
  ;;
 status)
  if [[ -f "$report_base/mysql.pid" ]]; then ps -p "$(cat "$report_base/mysql.pid")" -o pid,etime,args; else echo '未发现报表MySQL进程记录';fi
  ;;
 *) echo '使用：mysql_reporting.sh start|status' >&2;exit 2;;
esac
