#!/usr/bin/env python3
"""Build the reviewed Apps controller with its locked dependency graph."""
import argparse
import hashlib
import json
import re
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
    # The host accepts the reviewed digest in every build. Compile the
    # controller from the locked package graph, including on development hosts.
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
        lock = json.loads((ROOT / 'ziran.lock').read_text())
        identity = lock['root']['dependencies']['apps']
        app = next(item for item in lock['packages'] if item['id'] == identity)
        controller_lock = json.loads((package / 'ziran.lock').read_text())
        toolchain = controller_lock['toolchain']
        compiler_root = Path(subprocess.check_output(
            [str(args.ziran.resolve()), 'pkg', 'path', 'ziran', '--locked'],
            cwd=package, text=True).strip())
        compiler = compiler_root / 'build/bin/ziran'
        tools = ('ziran', 'zi2zir', 'zi2zx')
        if any(not (compiler_root / 'build/bin' / name).is_file() for name in tools):
            subprocess.run(['make', '-j1', *('build/bin/' + name for name in tools)],
                           cwd=compiler_root, check=True)
        # The reviewed payload has its own compiler and dependency versions.
        # Breeze's unrelated root dependencies can conflict with those pins.
        # Retain the Apps alias, and let the package manager produce a coherent
        # controller-only graph from the reviewed package's existing pins.
        (context / 'ziran.toml').write_text(
            '[package]\nname = ' + json.dumps(lock['root']['name']) +
            '\nmodule_roots = ["src"]\n\n[toolchain]\ngit = ' +
            json.dumps(toolchain['url']) + '\nref = ' +
            json.dumps(toolchain['commit']) + '\n\n[dependencies.apps]\ngit = ' +
            json.dumps(app['url']) + '\nref = ' + json.dumps(app['commit']) + '\n')
        (context / 'src').mkdir(exist_ok=True)
        shutil.copyfile(package / 'ziran.lock', context / 'ziran.lock')
        subprocess.run([str(compiler), 'lock', '--offline'], cwd=context, check=True)
        subprocess.run(['python3', str(package / 'scripts/build-ui.py'),
                        '--output', str(args.output.resolve()), '--project', str(context),
                        '--compiler', str(compiler)], cwd=ROOT, check=True)
        expected = re.search(r'AppsControllerSha256\s*::\s*"([a-f0-9]{64})"',
                             (ROOT / 'src/apps/apps_controller.zi').read_text()).group(1)
        actual = hashlib.sha256((args.output / 'apps.zx').read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit('Apps controller does not match the reviewed host digest')


if __name__ == '__main__':
    main()
