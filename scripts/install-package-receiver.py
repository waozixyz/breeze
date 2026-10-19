#!/usr/bin/env python3
"""Install the existing signed package receiver, without publishing any package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def wrapper(store):
    return '''#!/usr/bin/python3
# Managed by Inbe package receiver.
import os, shlex, sys
store = STORE
original = os.environ.get("SSH_ORIGINAL_COMMAND", "")
arguments = shlex.split(original) if original else ["inbe-packages", *sys.argv[1:]]
if arguments != ["inbe-packages", store]:
    raise SystemExit("Only the configured signed package upload is permitted")
os.environ["SSH_ORIGINAL_COMMAND"] = shlex.join(arguments)
os.execv(sys.executable, [sys.executable, "/opt/daochi/inbe-package-receiver/package-release.py",
    "--receive-archive", "--store", store,
    "--publishers", "/opt/daochi/inbe-package-receiver/publishers.json"])
'''.replace('STORE', repr(store))


def install(target, store):
    if not re.fullmatch(r'[A-Za-z0-9_.@-]+', target) or target.startswith('-'):
        raise ValueError('invalid SSH target')
    if not store.startswith('/') or any(c in store for c in '\n\r\0'):
        raise ValueError('package store must be absolute')
    # The receiver imports the release format from the Apps package beside it.
    configuration = dict(store=store, files={
        'node_release.py': (ROOT / 'build/packages/apps/scripts/node_release.py').read_text(),
        'package-release.py': (ROOT / 'scripts/package-release.py').read_text(),
        'practice_content.py': (ROOT / 'scripts/practice_content.py').read_text(),
        'publishers.json': (ROOT / 'apps/publishers.json').read_text(),
        'inbe-packages': wrapper(store)})
    remote = r'''
from pathlib import Path
import fcntl, hashlib, json, os, subprocess, sys, tempfile
configuration = json.load(sys.stdin)
store = Path(configuration['store'])
if not store.is_dir() or store.is_symlink():
    raise RuntimeError('Refusing an absent or symlinked package store')
lock = open('/var/lock/daochi-deploy.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX)
directory = Path('/opt/daochi/inbe-package-receiver')
launcher = Path('/usr/local/bin/inbe-packages')
if launcher.exists() and 'Managed by Inbe package receiver.' not in launcher.read_text():
    raise RuntimeError('Refusing to replace an unrelated package launcher')
if directory.exists() and not (directory / 'managed.json').exists():
    raise RuntimeError('Refusing to replace an unmanaged receiver')
directory.mkdir(mode=0o755, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='receiver-', dir=directory) as temporary:
    stage = Path(temporary)
    for name, text in configuration['files'].items():
        (stage / name).write_text(text)
    subprocess.run([sys.executable, '-m', 'py_compile', str(stage / 'node_release.py'),
                    str(stage / 'package-release.py'), str(stage / 'practice_content.py'),
                    str(stage / 'inbe-packages')], check=True)
    subprocess.run([sys.executable, str(stage / 'package-release.py'), '--help'],
                    check=True, stdout=subprocess.DEVNULL)
    hashes = {}
    for name in ('node_release.py', 'practice_content.py', 'publishers.json', 'package-release.py'):
        target = directory / name
        (stage / name).chmod(0o644)
        os.replace(stage / name, target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    # The small launcher is installed last, after its imports are ready.
    (stage / 'inbe-packages').chmod(0o755)
    os.replace(stage / 'inbe-packages', launcher)
    hashes['inbe-packages'] = hashlib.sha256(launcher.read_bytes()).hexdigest()
    receipt = dict(installed=True, package_store=str(store), files=hashes,
                   packages_published=False)
    (directory / 'managed.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
'''
    options = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ConnectTimeout=8', '--', target, 'python3 -c ' + shlex.quote(remote)]
    result = subprocess.run(options, input=json.dumps(configuration), text=True,
                            capture_output=True, check=True)
    receipt = json.loads(result.stdout)
    saved = ROOT / 'backup/practice-downloads/receiver-install.json'
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps(receipt, indent=2) + '\n')
    print('Signed package receiver installed; no packages published.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ssh-target', required=True)
    parser.add_argument('--store', required=True)
    arguments = parser.parse_args()
    install(arguments.ssh_target, arguments.store)
