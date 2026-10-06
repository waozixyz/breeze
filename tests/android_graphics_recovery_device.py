#!/usr/bin/env python3
"""Compare Inbe's visible graphics across lifecycle changes on the dev Moto."""
import argparse
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

from PIL import Image, ImageChops, ImageStat

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host', default='wao@thinkpad.local')
parser.add_argument('--serial', default='ZE2223BQZT')
parser.add_argument('--package', default='xyz.waozi.inbe.debug')
parser.add_argument('--cycles', type=int, default=10)
parser.add_argument('--output', type=Path, default=Path('build/android/graphics-recovery'))
args = parser.parse_args()
if args.serial != 'ZE2223BQZT':
    parser.error('This test is restricted to the development Moto; never use the Pixel.')
if args.package not in ('xyz.waozi.inbe.debug', 'xyz.waozi.inbe'):
    parser.error('This test may operate only on Inbe.')
if args.cycles < 1:
    parser.error('--cycles must be positive')
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
    os.environ.pop(key, None)
args.output.mkdir(parents=True, exist_ok=True)


def adb(*command, binary=False):
    remote = shlex.join(['adb', '-s', args.serial, *map(str, command)])
    result = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', args.host, remote],
        capture_output=True, timeout=30, check=True)
    return result.stdout if binary else result.stdout.decode().strip()


def start():
    output = adb('shell', 'am', 'start', '-W', '-n',
                 args.package + '/xyz.waozi.inbe.MainActivity')
    if 'Status: ok' not in output:
        raise RuntimeError('Inbe did not start: ' + output)
    time.sleep(3)


def frame(name):
    focus = adb('shell', 'dumpsys', 'window', 'windows')
    current = next((line for line in focus.splitlines() if 'mCurrentFocus=' in line), '')
    if args.package + '/xyz.waozi.inbe.MainActivity' not in current:
        raise RuntimeError('Refusing to capture a window other than Inbe: ' + current)
    if adb('shell', 'pidof', args.package) != pid:
        raise RuntimeError('Inbe restarted during the recovery test')
    data = adb('exec-out', 'screencap', '-p', binary=True)
    (args.output / (name + '.png')).write_bytes(data)
    image = Image.open(io.BytesIO(data)).convert('RGB')
    # Exclude changing Android status/navigation bars. The app, including its
    # banners and bottom navigation icons, remains inside the comparison.
    width, height = image.size
    report.setdefault('frame_sizes', {})[name] = [width, height]
    return image.crop((0, int(height * .05), width, int(height * .94)))


def compare(reference, actual, name):
    if reference.size != actual.size:
        raise RuntimeError(name + ': app dimensions changed unexpectedly')
    difference = ImageChops.difference(reference, actual)
    error = sum(ImageStat.Stat(difference).mean) / 3
    width, height = difference.size
    worst_tile = 0.0
    for row in range(8):
        for column in range(4):
            tile = difference.crop((column * width // 4, row * height // 8,
                                    (column + 1) * width // 4, (row + 1) * height // 8))
            worst_tile = max(worst_tile, sum(ImageStat.Stat(tile).mean) / 3)
    # Allow minor antialiasing differences, but reject a missing banner,
    # font atlas replacing an image, or black navigation icons.
    if error > 1.5 or worst_tile > 3.0:
        difference.save(args.output / (name + '-difference.png'))
        raise RuntimeError(f'{name}: visible graphics changed (mean {error:.3f}, tile {worst_tile:.3f})')
    results.append({'case': name, 'mean_pixel_error': error, 'worst_tile_error': worst_tile})
    print(f'{name}: PASS (mean pixel error {error:.3f})', flush=True)


def setting(name, value):
    if value == 'null':
        adb('shell', 'settings', 'delete', 'system', name)
    else:
        adb('shell', 'settings', 'put', 'system', name, value)


if adb('get-state') != 'device':
    raise RuntimeError('Moto is not authorized and ready')
original_rotation = adb('shell', 'settings', 'get', 'system', 'user_rotation')
original_accelerometer = adb('shell', 'settings', 'get', 'system', 'accelerometer_rotation')
results = []
pid = ''
report = {'serial': args.serial, 'package': args.package, 'passed': False, 'cases': results}
try:
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
    adb('shell', 'wm', 'dismiss-keyguard')
    setting('accelerometer_rotation', '0')
    setting('user_rotation', '0')
    start()
    pid = adb('shell', 'pidof', args.package)
    if not pid:
        raise RuntimeError('Inbe is not running')
    reference = frame('portrait-reference')
    for cycle in range(args.cycles):
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        time.sleep(2)
        start()
        name = f'resume-{cycle + 1:02}'
        compare(reference, frame(name), name)

    references = {0: reference}
    for cycle in range(2):
        for rotation in (1, 2, 3, 0):
            setting('user_rotation', str(rotation))
            time.sleep(4)
            name = f'rotation-{cycle + 1}-{rotation}'
            actual = frame(name)
            if rotation not in references:
                references[rotation] = actual
                print(name + ': reference recorded', flush=True)
            else:
                compare(references[rotation], actual, name)

    if references[1].size == references[0].size:
        raise RuntimeError('No actual landscape rotation occurred; use System orientation in Inbe.')

    for cycle in range(3):
        adb('shell', 'input', 'keyevent', 'KEYCODE_SLEEP')
        time.sleep(2)
        adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
        adb('shell', 'wm', 'dismiss-keyguard')
        start()
        name = f'screen-wake-{cycle + 1}'
        compare(reference, frame(name), name)
    report['passed'] = True
    report['pid'] = pid
finally:
    setting('user_rotation', original_rotation)
    setting('accelerometer_rotation', original_accelerometer)
    if pid:
        logs = adb('logcat', '-d', '--pid=' + pid, '-v', 'brief')
        (args.output / 'inbe-logcat.txt').write_text(logs)
        report['graphics_info_log_messages'] = logs.count('Reloading graphics resources')
        report['info_logs_may_be_disabled'] = True
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
