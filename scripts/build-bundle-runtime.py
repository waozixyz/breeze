#!/usr/bin/env python3
"""Build the pinned Ziran host runtime for an app's target without source copies.

Node apps are ZX bundles, so the runtime carries Ziran's instruction engine; a
BOOTSTRAP=1 runtime opens no bundle. Ziran builds its own host compiler with
HOST_CC for these cross builds and makes the Wasm private-symbol headers.
Ziran's generated C comes from the pinned toolchain's own host zi2c
(GEN_ZI2C), not from a zi2c built for the target.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--host-zi2c", type=Path)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--cc", required=True)
p.add_argument("--ar", default="ar")
p.add_argument("--objcopy", default="objcopy")
p.add_argument("--flags", default="-O2 -fPIC")
p.add_argument("--wasm", action="store_true")
p.add_argument("--jobs", type=int, default=(
    os.environ.get("ZIRAN_JOBS") or os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL") or "1"
))
a = p.parse_args()
if a.jobs < 1:
    p.error("--jobs must be positive")
source = a.source.resolve()
output = a.output.resolve()
host_zi2c = (a.host_zi2c or source / "build/bin/zi2c").resolve()
if not host_zi2c.is_file():
    raise SystemExit(f"{host_zi2c} is missing; build the pinned toolchain first")
# Ziran's make compares file times, and a newly pinned toolchain's sources can
# be older than the last runtime built here, so the output records the
# checkout and host generator it was built from. A changed generator must not
# reuse generated C from another compiler payload, even at the same path.
marker = output / ".toolchain-source"
with host_zi2c.open("rb") as compiler:
    compiler_digest = hashlib.file_digest(compiler, "sha256").hexdigest()
identity = json.dumps({
    "source": str(source), "host_zi2c": str(host_zi2c), "sha256": compiler_digest
}, sort_keys=True)
if output.exists() and (not marker.is_file() or marker.read_text() != identity):
    shutil.rmtree(output)
output.mkdir(parents=True, exist_ok=True)
command = [
    "make",
    "-j" + str(a.jobs),
    "-C",
    str(source),
    "BUILD_DIR=" + str(output),
    "CC=" + a.cc,
    "AR=" + a.ar,
    "OBJCOPY=" + a.objcopy,
    "CFLAGS=" + a.flags,
    "FRAMEFLAGS=-Wframe-larger-than=16384",
    "GEN_ZI2C=" + str(host_zi2c),
]
if a.wasm:
    command += ["TARGET_MACHINE=wasm32-unknown-emscripten"]
command += [str(output / "libziran.a")]
subprocess.run(command, check=True)
marker.write_text(identity)
