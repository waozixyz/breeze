#!/usr/bin/env python3
"""Run the focused shader regression on Alpha with the canonical banner art."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw


PRACTICES = ('whm', 'patterns', 'meditation', 'astral_projection', 'sunsalutation', 'taichi', 'workout')
THEMES = ('light', 'dark')


def verify_layers(assets):
    for practice, prefix in [(practice, 'banner') for practice in PRACTICES] + [('workout', 'banner-short')]:
        layers = [assets / practice / f'{prefix}-{part}.webp' for part in ('landscape', 'character')]
        if not any(path.is_file() for path in layers):
            continue
        for path in layers:
            with Image.open(path) as image:
                if (image.format, image.size, image.n_frames, image.mode) != ('WEBP', (1536, 768), 1, 'RGBA'):
                    raise ValueError(f'{path} must be a single-frame 1536 x 768 RGBA WebP')
                if image.getchannel('A').getextrema() != (0, 255):
                    raise ValueError(f'{path} must have both transparent and opaque pixels')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--review', type=Path, help='write a composed GPU review sheet')
    args = parser.parse_args()
    sheet = Image.new('RGB', (776, 7 * 220), '#1b2735') if args.review else None
    captions = ImageDraw.Draw(sheet) if sheet else None
    if os.uname().nodename.split('.')[0] != 'alpha':
        parser.error('run native banner tests on Alpha')
    executable = args.executable.resolve(strict=True)
    verify_layers(args.assets)
    environment = os.environ.copy()
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'WAYLAND_SOCKET', 'XAUTHORITY', 'GDK_DISPLAY',
                 'DBUS_SESSION_BUS_ADDRESS', 'DBUS_STARTER_ADDRESS', 'SESSION_MANAGER'):
        environment.pop(name, None)
    environment.update(EGL_PLATFORM='surfaceless', HARMONY_DESKTOP_RECOVERY='0', YUE_DESKTOP_RECOVERY='0')
    total = 0
    with tempfile.TemporaryDirectory(prefix='banner-test-', dir=executable.parent) as temporary:
        private = Path(temporary)
        for name in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME',
                     'XDG_RUNTIME_DIR'):
            path = private / name.lower()
            path.mkdir(mode=0o700)
            environment[name] = str(path)
        overlay = private / 'overlay.rgba'
        for row, practice in enumerate(PRACTICES):
            for column, theme in enumerate(THEMES):
                relative = Path(practice) / f'banner-{theme}.webp'
                path = args.assets / relative
                size = path.stat().st_size
                total += size
                if size > 180_000:
                    raise ValueError(f'{relative} - {size} bytes exceeds the 180 KB banner budget')
                with Image.open(path) as image:
                    if (image.format, image.size, image.n_frames, image.mode) != ('WEBP', (1536, 768), 1, 'RGB'):
                        raise ValueError(f'{relative} must be a single-frame 1536 x 768 RGB WebP')
                    original = image.convert('RGBA').resize((384, 192), Image.Resampling.LANCZOS)
                print(f'{relative} ({size} bytes)', flush=True)
                command = [executable, f'assets/practices/{relative.as_posix()}']
                if sheet:
                    overlay.touch()
                    command.append(overlay)
                subprocess.run(command, env=environment, check=True)
                if sheet:
                    sky = Image.frombytes('RGBA', (576, 288), overlay.read_bytes()).resize(
                        original.size, Image.Resampling.LANCZOS)
                    x, y = column * 392, row * 220
                    captions.text((x + 4, y + 5), f'{practice} · {theme}', fill='white')
                    sheet.paste(Image.alpha_composite(original, sky).convert('RGB'), (x, y + 23))
    if total > 1_500_000:
        raise ValueError(f'{total} bytes exceeds the 1.5 MB banner budget')
    print(f'14 procedural sky and water overlays verified, {total} bytes of static fallback art')
    if sheet:
        sheet.save(args.review)


if __name__ == '__main__':
    main()
