"""Where the practice media is on disk.

The practices' pictures, course data and recordings live in the
practices package (https://github.com/waozixyz/practices),
pinned in ziran.lock and linked at build/packages/practices. Packages
keep their resources under assets/practices/, so a packaged path such as
assets/practices/taichi/course.tch names MEDIA / 'taichi/course.tch'.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'build/packages/practices'
PREFIX = 'assets/practices/'


def media_path(path):
    """The file on disk for a packaged path, or for a path in the project."""
    path = str(path)
    if path.startswith(PREFIX):
        return MEDIA / path[len(PREFIX):]
    return ROOT / path


def packaged_path(file):
    """The packaged path of a file in the practice media."""
    return PREFIX + Path(file).resolve().relative_to(MEDIA.resolve()).as_posix()


def writable_media():
    """The media checkout generators may write into: a working repository
    mapped in ziran.local.toml, never the locked package cache."""
    cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'ziran'
    if not MEDIA.is_dir() or MEDIA.resolve().is_relative_to(cache.resolve()):
        raise SystemExit(f'{MEDIA} is the locked package; map practices to your '
                         'practices checkout in ziran.local.toml to change its media')
    return MEDIA
