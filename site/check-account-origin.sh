#!/bin/sh
set -eu
host=${1:?Usage: check-account-origin.sh HOST}
case "$host" in
    innerbreeze.org|inbe.waozi.xyz) ;;
    *) exit 2 ;;
esac
for route in account/delete-with-key sync/challenge sync/login; do
    headers=$(curl -fsS --max-time 20 -D - -o /dev/null -X OPTIONS \
        -H "Origin: https://$host" \
        -H 'Access-Control-Request-Method: POST' \
        -H 'Access-Control-Request-Headers: content-type' \
        "https://api.waozi.xyz/api/v1/$route") || exit 1
    if ! printf '%s\n' "$headers" | awk -v origin="https://$host" '
        { sub(/\r$/, ""); line = tolower($0) }
        line == "access-control-allow-origin: " origin { allowed = 1 }
        line ~ /^access-control-allow-methods:/ { post = line ~ /[ ,:]post([ ,]|$)/ }
        line ~ /^access-control-allow-headers:/ { json = line ~ /[ ,:]content-type([ ,]|$)/ }
        END { exit !(allowed && post && json) }
    '; then
        printf 'Account API does not allow https://%s on %s\n' "$host" "$route" >&2
        exit 1
    fi
done
printf 'Verified sync and account deletion from https://%s\n' "$host"
