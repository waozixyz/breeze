#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
revision=${1:?Usage: verify-deployment.sh REVISION}
app_host=${SITE_APP_HOST:-innerbreeze.org}
verify_asset() {
    route=$1
    file=$2
    host=${3:-innerbreeze.org}
    attempt=1
    while [ "$attempt" -le 5 ]; do
        if curl -fsS --compressed --max-time 20 "https://$host$route?revision=$revision" | cmp -s - "$file"; then
            printf 'Verified %s\n' "$route"
            return
        fi
        attempt=$((attempt + 1))
        sleep 3
    done
    printf 'Production asset differs: %s\n' "$route" >&2
    return 1
}
verify_asset / build/site/index.html
verify_asset /css/landing.css build/site/css/landing.css
verify_asset /robots.txt build/site/robots.txt
verify_asset /sitemap.xml build/site/sitemap.xml
verify_asset /build/web/ build/site/build/web/index.html "$app_host"
verify_asset /build/telegram/ build/site/build/telegram/index.html "$app_host"
verify_asset /delete-account build/site/delete-account.html "$app_host"
verify_asset /apt/dists/stable/InRelease build/site/apt/dists/stable/InRelease
missing_status=$(curl -sS --max-time 20 -o /dev/null -w '%{http_code}' "https://innerbreeze.org/website-missing-route?revision=$revision")
test "$missing_status" = 404
printf 'Verified missing route returns HTTP 404\n'
for host in inbe.waozi.xyz breeze.waozi.xyz; do
    path='/privacy?source=previous%2Fsite&lang=en'
    result=$(curl -sS --max-time 20 -o /dev/null -w '%{http_code} %{redirect_url}' "https://$host$path")
    test "$result" = "308 https://innerbreeze.org$path"
    result=$(curl -fsSL --max-time 20 --max-redirs 4 -o /dev/null -w '%{url_effective}' "http://$host$path")
    test "$result" = "https://innerbreeze.org$path"
    printf 'Verified redirect from %s\n' "$host"
done
if [ "$app_host" = inbe.waozi.xyz ]; then
    for route in /build/web/ /build/telegram/ /delete-account; do
        route="$route?source=site%2Flaunch&lang=en"
        result=$(curl -sS --max-time 20 -o /dev/null -w '%{http_code} %{redirect_url}' "https://innerbreeze.org$route")
        test "$result" = "302 https://$app_host$route"
        result=$(curl -fsSL --max-time 20 --max-redirs 2 -o /dev/null -w '%{url_effective}' "https://innerbreeze.org$route")
        test "$result" = "https://$app_host$route"
        printf 'Verified account origin handoff for %s\n' "$route"
    done
fi
