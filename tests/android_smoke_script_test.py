#!/usr/bin/env python3
"""Exercise launch failures and process deaths without a device or display."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
fake_adb = '''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
path = Path(os.environ['SMOKE_STATE'])
state = json.loads(path.read_text()) if path.exists() else {'calls': [], 'polls': 0, 'home': False}
args = sys.argv[1:]
assert args[:2] == ['-s', 'emulator-5584'], args
args = args[2:]
state['calls'].append(args)
mode = os.environ['SMOKE_CASE']
if args[:2] == ['shell', 'pidof']:
    assert args[2] == 'xyz.waozi.inbe.debug', args
    state['polls'] += 1
    dead = mode == 'startup_crash' or (mode == 'crash' and state['polls'] > 1) or (mode == 'background_crash' and state['home'])
    if not dead:
        print('84' if mode == 'restart' and state['polls'] > 1 else '42')
elif args[:3] == ['shell', 'am', 'start']:
    assert 'xyz.waozi.inbe.debug/xyz.waozi.inbe.MainActivity' in args, args
    print('Error type 3: activity does not exist' if mode == 'launch_error' else 'Status: ok')
elif args[:3] == ['shell', 'input', 'keyevent']:
    state['home'] = True
elif args[:4] == ['shell', 'dumpsys', 'activity', 'activities']:
    print('mResumedActivity: other.app/.Activity' if mode == 'not_foreground' else 'mResumedActivity: xyz.waozi.inbe.debug/.MainActivity')
elif args[:1] == ['logcat']:
    print('E AndroidRuntime: diagnostic from an unrelated process')
path.write_text(json.dumps(state))
'''

with tempfile.TemporaryDirectory(prefix="android-smoke-", dir=root / "build") as directory:
    work = Path(directory)
    sdk = work / "sdk"
    (sdk / "platform-tools").mkdir(parents=True)
    adb = sdk / "platform-tools/adb"
    adb.write_text(fake_adb)
    adb.chmod(0o755)
    apk = work / "app.apk"
    apk.touch()
    for mode in ("healthy", "launch_error", "startup_crash", "crash",
                 "restart", "background_crash", "not_foreground"):
        state = work / f"{mode}.json"
        env = os.environ.copy()
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        env.update(ANDROID_HOME=str(sdk), ANDROID_SDK_ROOT=str(sdk),
                   ANDROID_SMOKE_SKIP_EMULATOR="1", ANDROID_SMOKE_APK=str(apk),
                   ANDROID_SMOKE_SERIAL="emulator-5584",
                   ANDROID_SMOKE_OBSERVATIONS="2", ANDROID_SMOKE_INTERVAL="0",
                   ANDROID_SMOKE_LOG_DIR=str(work / mode),
                   SMOKE_STATE=str(state), SMOKE_CASE=mode)
        result = subprocess.run(["sh", str(root / "scripts/android-smoke-test.sh")],
                                cwd=root, env=env, capture_output=True, text=True)
        assert (result.returncode == 0) == (mode == "healthy"), (mode, result.stdout, result.stderr)
        calls = json.loads(state.read_text())["calls"]
        assert ["install", "-r", "-t", str(apk)] in calls
        assert (work / mode / "android-smoke-logcat.txt").exists()
print("Android smoke: launch status, correct app ID, process death/restart and resume checks passed")
