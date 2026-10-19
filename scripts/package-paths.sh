#!/bin/sh
# Prints --module-path NAME=DIR for every linked dependency, so Inbe's builds
# import a package's modules as NAME/Module. scripts/packages.sh links each
# package under build/packages.
set -eu
packages=${1:-build/packages}
for path in kryon=kryon/src/ui kryon=kryon/src/backend apps=apps/src \
    crypto=crypto/src self=self/src plot=plot/src qrcode=qrcode/src \
    oqs=oqs/src mingcute=mingcute/src daochi_client=daochi-client; do
    printf '%s\n' --module-path "${path%%=*}=$packages/${path#*=}"
done
