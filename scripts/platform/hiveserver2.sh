#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
runtime="$project_root/output/hiveserver2"
mkdir -p "$runtime"
managed_running() {
  [[ -f "$runtime/pid" ]] || return 1
  local service_pid process_args
  service_pid=$(cat "$runtime/pid")
  [[ "$service_pid" =~ ^[0-9]+$ ]] || return 1
  process_args=$(ps -p "$service_pid" -o args= || true)
  [[ "$process_args" == *hiveserver2* ]]
}
case "${1:-status}" in
 start)
  if managed_running; then
    echo '本脚本管理的HiveServer2已在运行'; exit 0
  fi
  # Keep this single-machine development endpoint on loopback.
  echo "$$" > "$runtime/pid"
  export HADOOP_HEAPSIZE_MAX=512
  exec "$HIVE_HOME/bin/hive" --service hiveserver2 \
    --hiveconf hive.execution.engine=tez \
    --hiveconf hive.tez.container.size=512 \
    --hiveconf hive.tez.java.opts=-Xmx384m \
    --hiveconf hive.local.time.zone=Asia/Shanghai \
    --hiveconf hive.server2.thrift.bind.host=127.0.0.1 \
    --hiveconf hive.server2.thrift.port=10000 \
    --hiveconf hive.server2.webui.host=127.0.0.1 \
    --hiveconf hive.server2.webui.port=10002 \
    --hiveconf hive.server2.enable.doAs=false \
    --hiveconf hive.server2.authentication=NONE \
    > "$runtime/server.log" 2>&1 < /dev/null
  ;;
 stop)
  if [[ ! -f "$runtime/pid" ]]; then echo '未找到本脚本的服务记录'; exit 0; fi
  service_pid=$(cat "$runtime/pid")
  if [[ ! "$service_pid" =~ ^[0-9]+$ ]]; then echo '进程记录格式错误' >&2; exit 1; fi
  args=$(ps -p "$service_pid" -o args= || true)
  if [[ "$args" != *hiveserver2* ]]; then echo '进程已退出或身份不符，不发送停止信号'; exit 0; fi
  kill -TERM "$service_pid"
  timeout 20 tail --pid="$service_pid" -f /dev/null
  echo '本脚本启动的HiveServer2已停止'
  ;;
 status)
  if managed_running; then
    ps -p "$(cat "$runtime/pid")" -o pid,etime,args
  else echo '本脚本未发现仍在运行的HiveServer2'; fi
  ;;
 *) echo '使用：bash scripts/platform/hiveserver2.sh start|stop|status' >&2;exit 2;;
esac
