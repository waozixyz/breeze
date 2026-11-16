#!/usr/bin/env python3
"""Build the reviewed Apps controller with its locked dependency graph."""
import argparse
import os
import shlex
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module_roots(manifest):
    text = manifest.read_text()
    try:
        import tomllib
        return tomllib.loads(text)['package']['module_roots']
    except ModuleNotFoundError:
        # Python before 3.11, as on the Ubuntu 22.04 package builders: the
        # manifest keeps module_roots as one list of strings on one line.
        import ast
        import re
        return ast.literal_eval(re.search(r'^module_roots\s*=\s*(\[[^\]]*\])', text, re.M).group(1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ziran', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Development hosts use the same canonical overrides as every other
    # package in this build. Release builds retain the reviewed locked graph.
    locked = '--locked' in shlex.split(os.environ.get('PACKAGE_FLAGS', ''))
    if not locked and (ROOT / 'ziran.local.toml').exists():
        package = Path(subprocess.check_output(
            [str(args.ziran.resolve()), 'pkg', 'path', 'apps'], cwd=ROOT, text=True).strip())
        subprocess.run(['python3', str(package / 'scripts/build-ui.py'),
                        '--output', str(args.output.resolve()), '--project', str(ROOT),
                        '--compiler', str(args.ziran.resolve())], cwd=ROOT, check=True)
        return
    # Only package metadata lives here. Source remains in the package cache;
    # the owner's local development overrides are never changed.
    with tempfile.TemporaryDirectory(prefix='apps-lock-', dir=ROOT / 'build') as directory:
        context = Path(directory)
        for name in ('ziran.toml', 'ziran.lock'):
            shutil.copyfile(ROOT / name, context / name)
        # Ziran resolves a project only when its module roots exist; the
        # controller needs none of this app's modules, so they stay empty.
        for directory in module_roots(ROOT / 'ziran.toml'):
            (context / directory).mkdir(parents=True, exist_ok=True)
        package = Path(subprocess.check_output(
            [str(args.ziran.resolve()), 'pkg', 'path', 'apps', '--locked'],
            cwd=context, text=True).strip())
        subprocess.run(['python3', str(package / 'scripts/build-ui.py'),
                        '--output', str(args.output.resolve()), '--project', str(context),
                        '--compiler', str(args.ziran.resolve())], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
