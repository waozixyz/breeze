"""Compile persistent nested-app addresses with the intended package toolchain."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ziran", required=True)
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--apps", type=Path, required=True)
    parser.add_argument("--daochi-client", type=Path, required=True)
    args = parser.parse_args()
    env = {key: value for key, value in os.environ.items()
           if key not in {"DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"}}
    work = ROOT / "build/app-locations-test"
    generated = work / "c"
    generated.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        args.ziran, "build", "--target=c", "--no-main", "--root", str(ROOT / "tests"),
        "--module-path", "apps=" + str(args.apps / "src"),
        "--module-path", str(args.daochi_client),
        "--module-path", str(args.toolchain / "std"), "--entry", "app_locations_behavior:Check",
        "-o", str(generated), str(ROOT / "tests/app_locations_behavior.zi")
    ], cwd=ROOT, env=env, check=True)
    (work / "main.c").write_text(
        '#include "app_locations_behavior.h"\n#include <stdio.h>\n'
        'int main(void) { int r=Check(); if(r) fprintf(stderr,"App location check %d failed\\n",r); return r ? 1 : 0; }\n')
    includes = [argument for path in [generated, *sorted(generated.rglob("*"))]
                if path.is_dir() for argument in ("-iquote", str(path))]
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-O2", "-DZIRAN_BOUNDS_CHECK",
        "-I" + str(args.toolchain / "include"), *includes,
        str(work / "main.c"), *map(str, sorted(generated.rglob("*.c"))),
        "-lm", "-o", str(work / "test")
    ], cwd=ROOT, env=env, check=True)
    subprocess.run([str(work / "test")], cwd=ROOT, env=env, check=True)
    print("Nested addresses: identity/digest roundtrip, rollback, cycles, 80 levels and publisher/app storage isolation passed")


if __name__ == "__main__":
    main()
