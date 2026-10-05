#!/usr/bin/env python3
"""Build the pinned Ziran host runtime for an app's target without source copies."""

import argparse
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--cc", required=True)
p.add_argument("--ar", default="ar")
p.add_argument("--objcopy", default="objcopy")
p.add_argument("--flags", default="-O2 -fPIC")
p.add_argument("--wasm", action="store_true")
a = p.parse_args()
source = a.source.resolve()
output = a.output.resolve()
command = [
    "make",
    "-j4",
    "-C",
    str(source),
    "BOOTSTRAP=1",
    "BUILD_DIR=" + str(output),
    "CC=" + a.cc,
    "AR=" + a.ar,
    "OBJCOPY=" + a.objcopy,
    "CFLAGS=" + a.flags,
    "FRAMEFLAGS=-Wframe-larger-than=16384",
]
if a.wasm:
    private = output / "private"
    private.mkdir(parents=True, exist_ok=True)
    keywords = {
        "char",
        "const",
        "double",
        "float",
        "int",
        "long",
        "short",
        "signed",
        "sizeof",
        "struct",
        "union",
        "unsigned",
        "void",
    }
    for group in ["parse", "check", "emit", "vm"]:
        header = (source / f"cmd/zir/zir_{group}_internal.h").read_text()
        block = header.split("#pragma GCC visibility push(hidden)", 1)[1].split(
            "#pragma GCC visibility pop", 1
        )[0]
        block = re.sub(r"/\*.*?\*/|//[^\n]*", "", block, flags=re.S)
        names = set(re.findall(r"\b([A-Za-z_]\w*)\s*\((?!\s*\*)", block)) - keywords
        content = "".join(
            f"#define {name} private_{group}_{name}\n" for name in sorted(names)
        )
        path = private / (group + ".h")
        if not path.exists() or path.read_text() != content:
            path.write_text(content)
    command += ["WASM_PRIVATE_HEADERS=" + str(private)]
command += [str(output / "libziran.a")]
subprocess.run(command, check=True)
