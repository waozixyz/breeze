#!/usr/bin/env python3
"""Run the fixed release candidate on physical Alpha without changing its tree."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path.cwd()
SSH = ['ssh', '-F', str(Path.home() / '.ssh/alpha.conf'), 'alpha']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def remote(command, **kwargs):
    return subprocess.run([*SSH, command], check=True, **kwargs)


def copy_objects(source, destination, commit):
    """Transfer missing Git objects only; never move refs or touch source files."""
    probe = remote(shlex.join(['git', '-C', destination, 'rev-parse', 'HEAD']),
                   capture_output=True, text=True).stdout.strip()
    exists = subprocess.run([*SSH, shlex.join(['git', '-C', destination,
                            'cat-file', '-e', commit + '^{commit}'])], capture_output=True)
    if exists.returncode == 0:
        return
    if exists.returncode != 128:
        raise RuntimeError('Could not inspect Alpha candidate objects')
    revisions = commit + '\n'
    known = subprocess.run(['git', '-C', str(source), 'cat-file', '-e', probe + '^{commit}'],
                           capture_output=True)
    if known.returncode == 0:
        revisions += '^' + probe + '\n'
    producer = subprocess.Popen(['git', '-C', str(source), '-c', 'pack.threads=1', '-c', 'pack.windowMemory=64m',
                                 'pack-objects', '--stdout', '--revs'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    producer.stdin.write(revisions.encode())
    producer.stdin.close()
    try:
        consumer = subprocess.run([*SSH, shlex.join(['git', '-C', destination,
                                  'index-pack', '--stdin'])], stdin=producer.stdout)
    finally:
        producer.stdout.close()
        code = producer.wait()
    if code or consumer.returncode:
        raise RuntimeError('Candidate object transfer failed')
    remote(shlex.join(['git', '-C', destination, 'cat-file', '-e', commit + '^{commit}']))


def record_stamp(stamp, output, commit):
    """Accept only Alpha's real pass for the exact candidate content."""
    data = json.loads(stamp)
    identity = git('show', commit + ':scripts/phone-check.py')
    scope = {'__file__': str(ROOT / 'scripts/phone-check.py'), '__name__': 'release_identity'}
    exec(compile(identity, scope['__file__'], 'exec'), scope)
    expected_content = scope['release_content'](ROOT, commit)
    if (data.get('passed') is not True or data.get('commit') != commit
            or data.get('content') != expected_content):
        raise RuntimeError('Alpha did not produce a passing stamp for this candidate')
    destination = ROOT / output / 'stamp.json'
    for path in (ROOT / 'build', destination.parent, destination):
        if path.is_symlink():
            raise RuntimeError('Refusing symlink release output')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(stamp)
    print('release-ready: copied the actual Alpha pass stamp for ' + commit)


def main():
    commit = git('rev-parse', os.environ.get('RELEASE_READY_REVISION', 'HEAD') + '^{commit}')
    runtime = shutil.which(os.environ.get('JS_RUNTIME', 'bun'))
    if not runtime and 'JS_RUNTIME' not in os.environ:
        candidate = Path.home() / '.bun/bin/bun'
        runtime = str(candidate) if candidate.is_file() else None
    if not runtime or Path(runtime).name != 'bun':
        raise RuntimeError('Set JS_RUNTIME to the installed Bun executable')
    discovery = '''from pathlib import Path
import json,subprocess
root=Path.home()/'Projects/waozixyz/apps/breeze'
mesh=Path.home()/'Projects/ziranlang/mesh'
for path in (root,mesh):
 assert (path/'.git').exists(),str(path)
origin=subprocess.check_output(['git','-C',str(root),'remote','get-url','origin'],text=True).strip()
assert origin=='https://git.waozi.xyz/waozi/breeze.git',origin
print(json.dumps([str(root),str(mesh)]))'''
    root, mesh = json.loads(remote('python3 -c ' + shlex.quote(discovery),
                                  capture_output=True, text=True).stdout)
    copy_objects(ROOT, root, commit)
    if not sys.argv[1:]:
        mesh_commit = git('show', commit + ':.github/sync-test-server-commit')
        mesh_source = Path(os.environ.get('RELEASE_READY_MESH_SOURCE', ROOT / '../../../ziranlang/mesh')).resolve()
        copy_objects(mesh_source, mesh, mesh_commit)
    output = os.environ.get('RELEASE_READY_OUTPUT', 'build/release-ready')
    layout = git('show', commit + ':scripts/check-build-layout.py')
    output = subprocess.check_output([sys.executable, '-c', layout, output], text=True).strip()
    # Carry the explicitly selected runtime as a binary, independently of sources.
    remote('mkdir -p /tmp/breeze-release-tools')
    with open(runtime, 'rb') as stream:
        remote('cat > /tmp/breeze-release-tools/bun', stdin=stream)
    remote('chmod 755 /tmp/breeze-release-tools/bun')
    with open(runtime, 'rb') as stream:
        expected_runtime = hashlib.file_digest(stream, 'sha256').hexdigest()
    actual_runtime = remote('sha256sum /tmp/breeze-release-tools/bun', capture_output=True, text=True).stdout.split()[0]
    if actual_runtime != expected_runtime:
        raise RuntimeError('Alpha Bun differs from the explicitly selected runtime')
    environment = dict(RELEASE_READY_ROOT=root, RELEASE_READY_HOST='local',
                       RELEASE_READY_REVISION=commit, RELEASE_READY_OUTPUT=output,
                       RELEASE_READY_MESH_SOURCE=mesh, JS_RUNTIME='/tmp/breeze-release-tools/bun',
                       CC='/usr/bin/cc', HOST_CC='/usr/bin/cc', HARMONY_DESKTOP_RECOVERY='0')
    for name in ('RELEASE_READY_DNS', 'RELEASE_READY_INCREMENTAL', 'JS_TEST_FLAGS', 'ADDONS_LINTER'):
        if name in os.environ:
            environment[name] = os.environ[name]
    setup = '''import os,subprocess,sys
from pathlib import Path
root=sys.argv[1]
os.chdir(root)
os.environ.update(__import__('json').loads(sys.argv[2]))
for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'):
 os.environ.pop(key,None)
tools=Path('/tmp/breeze-container-tools')
paths=[str(Path.home()/'.local/bin'),'/usr/bin','/bin']
if (tools/'root/usr/bin/podman').is_file():
 paths.insert(0,str(tools/'root/usr/bin'))
 os.environ['CONTAINERS_CONF']=str(tools/'containers.conf')
os.environ['PATH']=':'.join(paths)
script=subprocess.check_output(['git','show',os.environ['RELEASE_READY_REVISION']+':scripts/release-ready.sh'],text=True)
os.execvp('sh',['sh','-c',script,'scripts/release-ready.sh',*sys.argv[3:]])'''
    command = ['systemd-run', '--user', '--scope', '--quiet', '--expand-environment=no', '--unit=breeze-release-ready-alpha',
               '-p', 'MemoryMax=' + os.environ.get('RELEASE_READY_MEMORY', '6G'),
               '-p', 'MemorySwapMax=0', '-p', 'CPUQuota=' + os.environ.get('RELEASE_READY_CPU', '200%'),
               '-p', 'AllowedCPUs=' + os.environ.get('RELEASE_READY_CPUS', '2,3'),
               '-p', 'TasksMax=1024', 'python3', '-c', setup, root,
               json.dumps(environment), *sys.argv[1:]]
    result = subprocess.run([*SSH, shlex.join(command)])
    if result.returncode:
        return result.returncode
    if not sys.argv[1:]:
        stamp = remote(shlex.join(['cat', root + '/' + output + '/stamp.json']), capture_output=True).stdout
        record_stamp(stamp, output, commit)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
