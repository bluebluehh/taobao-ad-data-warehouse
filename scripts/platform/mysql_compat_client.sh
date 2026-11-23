#!/usr/bin/env bash
# Rootless MariaDB command-line client for the independent MySQL 8 server.
# Keep --defaults-file/--no-defaults first in the caller's arguments.
set -euo pipefail
prefix=/opt/taobao/module/mysql-ubuntu-8.0.46/usr
exec "$prefix/bin/mysql.compat" "$@" --plugin-dir="$prefix/lib/mariadb-client-plugin"
