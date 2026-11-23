#!/usr/bin/env bash
set -euo pipefail
scheduler_home=/opt/taobao/module/apache-dolphinscheduler-3.3.2-bin
scheduler_data=/opt/taobao/data/scheduler
if [[ -f /opt/taobao/node-env.sh ]]; then source /opt/taobao/node-env.sh; fi
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-8-openjdk-amd64}"
export PATH="$JAVA_HOME/bin:$PATH"
case "${1:-status}" in
 start)
  test -f "$scheduler_data/conf/local-application.yaml"
  if [[ -f "$scheduler_data/server.pid" ]] && [[ $(ps -p "$(cat "$scheduler_data/server.pid")" -o args= || true) == *org.apache.dolphinscheduler.StandaloneServer* ]]; then
   echo '本脚本管理的调度服务已在运行';exit 0
  fi
  classpath="$scheduler_data/conf:$scheduler_home/standalone-server/conf"
  for module in api-server master-server worker-server alert-server standalone-server; do
   classpath="$classpath:$scheduler_home/$module/libs/*"
  done
  for plugin in alert-plugins datasource-plugins storage-plugins task-plugins; do
   classpath="$classpath:$scheduler_home/plugins/$plugin/*"
  done
  echo "$$" > "$scheduler_data/server.pid"
  cd "$scheduler_data"
  exec "$JAVA_HOME/bin/java" -Xms128m -Xmx512m -XX:MaxMetaspaceSize=256m -Duser.timezone=Asia/Shanghai \
   -cp "$classpath" org.apache.dolphinscheduler.StandaloneServer \
   --spring.config.additional-location="file:$scheduler_data/conf/local-application.yaml" \
   > "$scheduler_data/logs/startup.log" 2>&1
  ;;
 stop)
  test -f "$scheduler_data/server.pid" || exit 0
  service_pid=$(cat "$scheduler_data/server.pid")
  [[ "$service_pid" =~ ^[0-9]+$ ]] || exit 1
  args=$(ps -p "$service_pid" -o args= || true)
  [[ "$args" == *org.apache.dolphinscheduler.StandaloneServer* ]] || exit 0
  kill -TERM "$service_pid"
  timeout 30 tail --pid="$service_pid" -f /dev/null
  ;;
 status)
  if [[ -f "$scheduler_data/server.pid" ]]; then ps -p "$(cat "$scheduler_data/server.pid")" -o pid,etime,args;else echo '尚未启动调度服务';fi
  ;;
 *) echo '使用：dolphinscheduler.sh start|stop|status' >&2;exit 2;;
esac
