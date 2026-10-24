#!/usr/bin/env python3
"""Build the reviewed Apps controller with its locked dependency graph."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ziran', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Only package metadata lives here. Source remains in the package cache;
    # the owner's local development overrides are never changed.
    with tempfile.TemporaryDirectory(prefix='apps-lock-', dir=ROOT / 'build') as directory:
        context = Path(directory)
        for name in ('ziran.toml', 'ziran.lock'):
            shutil.copyfile(ROOT / name, context / name)
        package = Path(subprocess.check_output(
            [str(args.ziran.resolve()), 'pkg', 'path', 'apps', '--locked'],
            cwd=context, text=True).strip())
        subprocess.run(['python3', str(package / 'scripts/build-ui.py'),
                        '--output', str(args.output.resolve())], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
