#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

revision=$(git rev-parse --verify "${1:-HEAD}^{commit}")
# The native web producer reads these paths. Site templates and unreleased
# homepage notes do not affect the artifact.
{
    git ls-tree -r "$revision" -- Makefile mk src apps assets design locales scripts \
        manifest.json ziran.toml ziran.lock web-assets site-icons unpackaged_assets \
        .gitattributes .github/emscripten-version .github/apt/web-packages.txt \
        .github/scripts/install-apt-packages.sh \
        .github/actions/emscripten .github/actions/ziran-packages \
        site/web-build-key.sh site/web-build-receipt.sh
    git show "$revision:CHANGELOG.md" | sed -n '/^## \[[0-9]/,$p'
} | sha256sum | cut -d ' ' -f 1
