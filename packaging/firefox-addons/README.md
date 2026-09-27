# Firefox Add-on Source Build

This document is for Mozilla Add-ons reviewers and anyone who needs to rebuild
`inbe-firefox-addons.zip` from the source tree.

## Build Environment

The Firefox add-on build is a WebAssembly web build wrapped with the Firefox
extension manifest and background script. It is tested in CI on Ubuntu Linux.
FreeBSD can also be used when the same tools are available.

Required tools:

- POSIX shell (`sh`)
- GNU Make (`make` on Linux, usually `gmake` on FreeBSD)
- C/C++ build tools (`cc`, `ar`, standard libc headers)
- CMake
- Emscripten SDK with `emcc`, `emar`, and `emranlib` on `PATH`
- Node.js 22 or newer and npm
- `zip`
- `perl`
- Tcl (`tclsh`) for generating SQLite amalgamation from canonical source

Ubuntu package dependencies used by CI are listed in
`.github/apt/web-packages.txt` and can be installed with:

```sh
sudo apt-get update
sudo apt-get install -y build-essential zlib1g-dev zip tcl
```

Install Node.js 22 or newer from your system package manager, NodeSource, nvm,
or the official Node.js downloads. Verify it with:

```sh
node --version
npm --version
```

Install and activate Emscripten SDK. The CI build uses the latest emsdk release:

```sh
git clone --depth 1 https://github.com/emscripten-core/emsdk.git "$HOME/emsdk"
"$HOME/emsdk/emsdk" install latest
"$HOME/emsdk/emsdk" activate latest
. "$HOME/emsdk/emsdk_env.sh"
```

Verify Emscripten with:

```sh
emcc --version
```

The Mozilla linter is run through npm. The default build uses:

```sh
npx --yes addons-linter
```

You may pin or override it with `ADDONS_LINTER`, for example:

```sh
ADDONS_LINTER="npx --yes addons-linter@latest"
```

## Build Steps

From the repository root, including initialized submodules, run:

```sh
sh scripts/build-firefox-addons-source.sh
```

The script performs all technical build steps:

1. Selects one stable `WEB_CACHE_BUSTER` value for the run.
2. Prints relevant tool versions.
3. Builds packaged runtime assets.
4. Builds the Firefox add-on zip.
5. Runs Mozilla `addons-linter` against the zip.
6. Verifies the final zip exists.

Output:

```text
build/dist/inbe-firefox-addons.zip
```

For a deterministic cache-buster string, set `WEB_CACHE_BUSTER` explicitly:

```sh
WEB_CACHE_BUSTER=<source-commit-or-version> sh scripts/build-firefox-addons-source.sh
```

Without `WEB_CACHE_BUSTER`, the wrapper script uses the current git commit hash
when available, otherwise a timestamp selected once at script startup. The
Makefile itself still supports its normal local fallback behavior.

## SQLite Amalgamation

SQLite is pinned in `ziran.lock` as the official canonical source repository and
fetched to `build/packages/sqlite`.
The build generates `vendor-builds/sqlite/sqlite3.c` and `sqlite3.h` from that
source with SQLite's recommended amalgamation flow (`configure`, then
`make sqlite3.c sqlite3.h`). This keeps the Firefox source submission rooted in
the official SQLite source instead of depending on a checked-in generated
`vendor-builds` artifact.

## Firefox Packaging Notes

The normal web build injects a small inline bootstrap script. Firefox extension
CSP blocks inline JavaScript, so the Firefox package rule renders the same web
shell template with an external `extension_loader.js` script tag. The loader
source is kept in this directory and is copied into the generated add-on package.
