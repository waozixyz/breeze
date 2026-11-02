#!/usr/bin/env python3
"""Retain shipped apps and add complete local packages below one decimal MB."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil

from practice_content import bundle_assets


LIMIT_BYTES = 1_000_000
MANDATORY = ('lists', 'habits', 'practices', 'diary', 'lumi', 'leaderboard')


def cover_paths(catalog):
    for child in catalog.get('children', []):
        cover = child.get('cover', {})
        for path in (child.get('preview'), child.get('icon'), cover.get('portrait'),
                     cover.get('landscape'), cover.get('logo')):
            if path:
                yield path


def validate_dependencies(catalog):
    # Bundles contain their compiled imports. The only supported external
    # dependencies here are the catalog's separately installed game graph.
    if catalog.get('dependencies'):
        raise ValueError('unsupported required package dependencies')
    children = catalog.get('children', [])
    if len(children) > 16:
        raise ValueError('too many child packages')
    entries = {child['id']: child for child in children if 'id' in child}
    visiting, visited = set(), set()

    def visit(identity):
        if identity in visiting:
            raise ValueError('cyclic child dependencies')
        if identity in visited:
            return
        if identity not in entries:
            raise ValueError('missing child dependency')
        visiting.add(identity)
        for dependency in entries[identity].get('dependencies', []):
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in entries:
        visit(identity)


def validate_payload(item):
    if (not isinstance(item.get('sha256'), str)
            or not re.fullmatch('[0-9a-f]{64}', item['sha256'])
            or type(item.get('bytes')) is not int or not 8 <= item['bytes'] <= 64 * 1024 * 1024):
        raise ValueError('invalid catalog payload digest or size')


def inspect_bundle(path):
    data = path.read_bytes()
    assets = bundle_assets(data)
    catalog = json.loads(assets.get('assets/apps/catalog.json', b'{}'))
    validate_dependencies(catalog)
    external = {}
    for child in catalog.get('children', []):
        validate_payload(child)
        if child['bundle'] not in assets:
            external[child['sha256']] = child['bytes']
    art = catalog.get('art')
    if art:
        validate_payload(art)
    # Child games install separately with consent. Library artwork belongs to
    # the launcher: count it even when its catalog is only a few kilobytes.
    complete = True
    if not art:
        complete = all(p in assets for p in cover_paths(catalog))
    elif 'assets/apps/art.zx' in assets:
        data_art = assets['assets/apps/art.zx']
        complete = (len(data_art) == art['bytes'] and sha256(data_art).hexdigest() == art['sha256'])
        if complete:
            pictures = bundle_assets(data_art)
            complete = all(p in pictures or p in assets for p in cover_paths(catalog))
    art_bytes = art['bytes'] if art and 'assets/apps/art.zx' not in assets else 0
    return dict(bundle_bytes=len(data), complete_bytes=len(data) + art_bytes, complete=complete,
                required_art_bytes=art_bytes,
                optional_download_bytes=sum(external.values()),
                optional_downloads=external, sha256=sha256(data).hexdigest())


def stage(ledger, declarations, bundles, optional, destination):
    destination.mkdir(parents=True, exist_ok=True)
    # The historical shipped set is independent of size and sidebar choices.
    for name in MANDATORY:
        shutil.copyfile(bundles / (name + '.zx'), destination / (name + '.zx'))
    # This generated inventory is separate from the mandatory shipped set.
    # Reusing a staging directory must not leak an excluded/removed candidate.
    if optional.exists():
        shutil.rmtree(optional)
    optional.mkdir(parents=True)
    candidates = [(name, bundles.parent / 'node-apps' / (name + '.zx'), None)
                  for name in ledger.get('node_apps', {})]
    candidates += [(name, Path(item['path']), item)
                   for name, item in declarations.items()]
    report = dict(limit_bytes=LIMIT_BYTES, mandatory=list(MANDATORY), optional={})
    selected = []
    releases = {}
    for name, path, declaration in candidates:
        if (not name.isascii() or not name.replace('-', '').isalnum()
                or not name.islower() or name in report['optional'] or name in MANDATORY):
            raise ValueError('invalid or duplicate optional app name')
        info = inspect_bundle(path)
        if declaration and (declaration['sha256'] != info['sha256']
                            or declaration['bytes'] != info['bundle_bytes']
                            or declaration['id'] != 'inbe.' + name):
            raise ValueError('local app differs from its reviewed declaration')
        catalog = json.loads(bundle_assets(path.read_bytes()).get('assets/apps/catalog.json', b'{}'))
        art = catalog.get('art')
        resource = None
        if art and info['complete_bytes'] != info['bundle_bytes']:
            resource = path.parent / (name + '.games') / (art['sha256'] + '.zx')
            info['complete'] = (resource.is_file() and resource.stat().st_size == art['bytes']
                                and sha256(resource.read_bytes()).hexdigest() == art['sha256'])
            if info['complete']:
                pictures = bundle_assets(resource.read_bytes())
                packed = bundle_assets(path.read_bytes())
                info['complete'] = all(p in pictures or p in packed for p in cover_paths(catalog))
        forced = bool(declaration and declaration.get('bundled'))
        if forced and not info['complete']:
            raise ValueError('explicitly bundled app is missing required artwork')
        info['included'] = info['complete'] and (forced or info['complete_bytes'] < LIMIT_BYTES)
        info['explicit'] = forced
        report['optional'][name] = info
        if info['included']:
            shutil.copyfile(path, optional / (name + '.zx'))
            if resource:
                target = optional / name / resource.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(resource, target)
            selected.append(name)
            source = declaration or ledger['node_apps'][name]
            releases[name] = dict(id='inbe.' + name, version=source['version'],
                                  sequence=source.get('sequence', 1), host_api=source['host_api'],
                                  key_id=source.get('key_id', 'inbe-2026-10'),
                                  sha256=info['sha256'], bytes=info['bundle_bytes'],
                                  complete_bytes=info['complete_bytes'])
    (optional / 'catalog.txt').write_text(''.join(name + '\n' for name in selected))
    (optional / 'releases.json').write_text(json.dumps(releases, separators=(',', ':')) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundles', type=Path, default=Path('build/apps'))
    parser.add_argument('--optional', type=Path, default=Path('build/package-assets/inbe/assets/apps/bundled'))
    parser.add_argument('--mandatory', type=Path, default=Path('build/bundled-apps'))
    parser.add_argument('--report', type=Path, default=Path('build/small-app-bundling.json'))
    args = parser.parse_args()
    report = stage(json.loads(Path('apps/versions.json').read_text()),
                   json.loads(Path('apps/bundled.json').read_text()),
                   args.bundles, args.optional, args.mandatory)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    for name, info in report['optional'].items():
        print(f"{name}: {info['bundle_bytes']} package bytes, "
              + f"{info['complete_bytes']} bytes with required artwork, "
              + ('embedded offline' if info['included'] else 'separate optional download'))


if __name__ == '__main__':
    main()
