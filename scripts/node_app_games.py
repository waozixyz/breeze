#!/usr/bin/env python3
"""Verify a release's separate games against its authenticated catalog."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile

from practice_content import bundle_assets

GAME_LIMIT = 16
PAYLOAD_LIMIT = 64 * 1024 * 1024


def required_games(bundle):
    assets = bundle_assets(bundle.read_bytes())
    catalog = assets.get('assets/apps/catalog.json')
    if catalog is None:
        return set()
    children = json.loads(catalog)['children']
    if len(children) > GAME_LIMIT:
        raise ValueError('collection has too many games')
    names = set()
    for child in children:
        if child['bundle'] in assets:
            continue
        digest = child['sha256']
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid game digest in catalog')
        names.add(digest + '.zx')
    return names


def stage_games(bundle, archive, output):
    expected = required_games(bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='node-games-', dir=output.parent) as directory:
        staging = Path(directory) / 'games'
        staging.mkdir()
        seen = set()
        with tarfile.open(archive) as source:
            for member in source:
                if (member.name not in expected or member.name in seen or not member.isfile()
                        or not 8 <= member.size <= PAYLOAD_LIMIT):
                    raise ValueError('unexpected, repeated or invalid game archive entry')
                digest = sha256()
                total = 0
                with source.extractfile(member) as data, (staging / member.name).open('wb') as target:
                    while chunk := data.read(1024 * 1024):
                        total += len(chunk)
                        if total > member.size:
                            raise ValueError('game exceeds its declared archive size')
                        digest.update(chunk)
                        target.write(chunk)
                if total != member.size or digest.hexdigest() + '.zx' != member.name:
                    raise ValueError('game bytes differ from the authenticated catalog')
                with (staging / member.name).open('rb') as data:
                    if data.read(4) != b'ZX\0\0':
                        raise ValueError('game is not a ZX bundle')
                seen.add(member.name)
        if seen != expected:
            raise ValueError('game archive is missing a declared game')
        if output.exists():
            shutil.rmtree(output)
        staging.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.list:
        for name in sorted(required_games(args.bundle)):
            print(name)
    else:
        if args.archive is None or args.output is None:
            parser.error('give --archive and --output')
        stage_games(args.bundle, args.archive, args.output)


if __name__ == '__main__':
    main()
