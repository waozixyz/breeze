#!/bin/sh
HERE="${APP_DIR:-$(dirname "$(readlink -f "$0")")}"
export LD_LIBRARY_PATH="$HERE/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$HERE/usr/bin/breeze" "$@"
