"""Exercise production app frames on a private display and temporary data root."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
    ENV.pop(name, None)
ENV["YUE_DESKTOP_RECOVERY"] = "0"

WRAPPED_FUNCTIONS = (
    "InitAudioDevice", "IsAudioDeviceReady", "CloseAudioDevice",
    "LoadMusicStream", "IsMusicValid", "PlayMusicStream", "StopMusicStream",
    "UnloadMusicStream", "PauseMusicStream", "ResumeMusicStream",
    "IsMusicStreamPlaying", "UpdateMusicStream", "SetMusicVolume",
    "update_check_start", "app_play_bell_cue", "app_play_breath_cue",
)

objects = shlex.split((ROOT / sys.argv[4]).read_text())
main_objects = [path for path in objects if path.endswith("/generated/src/main.o")]
assert len(main_objects) == 1, "the native response file must have one app main"

with tempfile.TemporaryDirectory(prefix="music-navigation-", dir=ROOT / "build") as directory:
    work = Path(directory)
    response = work / "objects.rsp"
    response.write_text("\n".join(path for path in objects if path not in main_objects))
    binary = work / "test"
    command = shlex.split(sys.argv[1]) + shlex.split(sys.argv[2])
    command += ["-Wno-unused-function", "-Wno-unused-variable",
                str(ROOT / "tests/music_navigation_test.c"), "-o", str(binary),
                "@" + str(response)]
    command += ["-Wl,--wrap=" + name for name in WRAPPED_FUNCTIONS]
    command += shlex.split(sys.argv[3])
    subprocess.run(command, cwd=ROOT, env=ENV, check=True)

    test_env = dict(ENV)
    test_env["APP_DATA_ROOT"] = str(work / "data")
    test_env["APP_NO_TRAY"] = "1"
    test_env["LIBGL_ALWAYS_SOFTWARE"] = "1"
    command = ["timeout", "30s", "xvfb-run", "-a", "-n", "300",
               "-s", "-screen 0 1280x900x24", str(binary),
               str(ROOT / "test-fixtures/audio/autumn-sunset.mp3")]
    result = subprocess.run(command, cwd=ROOT, env=test_env,
                            capture_output=True, text=True)
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print(result.stdout.splitlines()[-1])
