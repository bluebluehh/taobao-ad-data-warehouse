#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export SUPERSET_CONFIG_PATH="$project_root/platform/superset/superset_config.py"
export FLASK_APP=superset
runtime="$project_root/output/superset"
mkdir -p "$runtime"
case "${1:-status}" in
 start)
  if [[ -f "$runtime/server.pid" ]] && [[ $(ps -p "$(cat "$runtime/server.pid")" -o args= || true) == *gunicorn* ]]; then echo 'Superset已在运行';exit 0;fi
  exec /opt/taobao/module/superset-6.1.0-venv/bin/gunicorn \
   --workers 1 --threads 2 --timeout 120 --bind 127.0.0.1:8089 \
   --pid "$runtime/server.pid" --access-logfile "$runtime/access.log" \
   --error-logfile "$runtime/error.log" 'superset.app:create_app()'
  ;;
 stop)
  test -f "$runtime/server.pid" || exit 0
  service_pid=$(cat "$runtime/server.pid")
  [[ "$service_pid" =~ ^[0-9]+$ ]] || exit 1
  args=$(ps -p "$service_pid" -o args= || true)
  [[ "$args" == *gunicorn* ]] || exit 0
  kill -TERM "$service_pid"
  timeout 25 tail --pid="$service_pid" -f /dev/null
  ;;
 status)
  if [[ -f "$runtime/server.pid" ]]; then ps -p "$(cat "$runtime/server.pid")" -o pid,etime,args;else echo '尚未启动Superset';fi
  ;;
 *) echo '使用：superset.sh start|stop|status' >&2;exit 2;;
esac
