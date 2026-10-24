#!/usr/bin/env python3
"""Build and publish Inbe's independently signed Daochi release v2 files."""
import argparse
from contextlib import ExitStack
import fcntl
import io
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import tempfile
import time
import sys
from urllib.parse import urlsplit
from urllib.error import HTTPError

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
# The release format and the apps the node offers come from the Apps package.
# Builds link it under build/packages; the node receiver installs it here.
sys.path.insert(0, str(ROOT / 'build/packages/apps/scripts'))
from practice_content import catalog_from_bundle, bundle_assets
import node_release
from node_release import (BUNDLED_IDS, IDENTIFIER, VERSION, atomic_write, import_node_app, node_app_id,
                          open_public_url, signing_message, upload, validate_release, version_tuple,
                          write_histories, write_history)
NAMES = ("habits", "practices", "lumi", "lists", "diary", "leaderboard", "inbe")
if {"inbe" if name == "inbe" else "inbe." + name for name in NAMES} != BUNDLED_IDS:
    raise SystemExit("Apps' node_release.py names other bundled apps than Inbe ships")


def stage(store, key_path, key_id, publishers_path=None, *, build_directory=None):
    build_directory = Path(build_directory) if build_directory is not None else ROOT / 'build'
    if not IDENTIFIER.fullmatch(key_id) or key_id in (".", ".."):
        raise ValueError("invalid publisher key ID")
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("publisher key must be Ed25519")
    public_key = key.public_key().public_bytes(serialization.Encoding.Raw,
                                             serialization.PublicFormat.Raw).hex()
    publishers = json.loads((publishers_path or ROOT / "apps/publishers.json").read_text())
    versions = json.loads((ROOT / "apps/versions.json").read_text())
    trusted = next((p for p in publishers if p["key_id"] == key_id and
                    p["public_key"] == public_key), None)
    ids = {versions["apps"][name]["id"] for name in NAMES}
    if trusted is None or not ids <= set(trusted["app_ids"]):
        raise ValueError("signing key must match the public key shipped in apps/publishers.json")
    releases = {}
    payloads = {}
    for name in NAMES:
        component = versions["apps"][name]
        sequence = component["sequence"]
        if not VERSION.fullmatch(component["version"]) or not 0 < sequence <= 2**31 - 1:
            raise ValueError(f"invalid {name} version or sequence")
        path = build_directory / ("inbe.zx" if name == "inbe" else f"cells/{name}.zx")
        data = path.read_bytes()
        if not data.startswith(b"ZX\0\0") or not 8 <= len(data) <= 64 * 1024 * 1024:
            raise ValueError(f"invalid {name} bundle")
        artifact = dict(variant="module", sha256=sha256(data).hexdigest(), size=len(data))
        dependencies = []
        if name == "inbe":
            for child in (name for name in NAMES if name != "inbe"):
                release = releases[child]
                nested = payloads[child]
                if data.count(nested) != 1:
                    raise ValueError(f"root does not contain the exact {child} release")
                dependencies.append(dict(app_id=release["app_id"], version=release["version"],
                                         sha256=release["artifacts"][0]["sha256"], size=len(nested)))
        value = dict(app_id=component["id"], sequence=sequence, version=component["version"],
                     runtime="kryon-app-v1", host_api=component.get("host_api", versions["host_api"]),
                     module_api=versions["module_api"], data_schema=0, key_id=key_id,
                     artifacts=[artifact], dependencies=sorted(dependencies, key=lambda d: d["app_id"]))
        value["signature"] = key.sign(signing_message(value)).hex()
        releases[name] = value
        payloads[name] = data
    store.mkdir(parents=True, exist_ok=True)
    content_payloads = []
    for pack in catalog_from_bundle(payloads['practices']):
        filename = (pack['practice'] + ('.' + pack['language'] if pack['language'] else '') +
                    ('.' + pack['voice'] if pack.get('voice') else '') + '.zx')
        data = (build_directory / 'practice-content' / filename).read_bytes()
        if len(data) != pack['size'] or sha256(data).hexdigest() != pack['sha256']:
            raise ValueError('practice content differs from its signed catalog')
        value = dict(releases['practices'])
        value['data_schema'] = 1
        value['artifacts'] = [dict(variant='module', sha256=pack['sha256'], size=len(data))]
        value['signature'] = key.sign(signing_message(value)).hex()
        content_payloads.append((pack['sha256'], data, value, pack.get('product', '')))
    # Validate all old pointers before publishing any new one. Use the same
    # per-app lock name as Daochi's staging tool.
    with ExitStack() as stack:
        for name in sorted(NAMES):
            directory = store / releases[name]["app_id"]
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock = stack.enter_context((directory / ".publish.lock").open("a+b"))
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = directory / "latest-v2.json"
            if current.exists():
                previous = json.loads(current.read_bytes())
                value = releases[name]
                if previous != value and (value["sequence"] <= previous["sequence"] or
                        tuple(map(int, value["version"].split("."))) <=
                        tuple(map(int, previous["version"].split(".")))):
                    raise ValueError(f"{name} changed: advance its version and sequence")
            value = releases[name]
            encoded = (json.dumps(value, separators=(",", ":")) + "\n").encode()
            payload = directory / (value["artifacts"][0]["sha256"] + ".zx")
            archive = directory / f"release-{value['sequence']}.json"
            if payload.exists() and payload.read_bytes() != payloads[name]:
                raise ValueError("immutable payload does not match its hash")
            if archive.exists() and archive.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
        # Content is installed before the harness advertises its hashes.
        for digest, data, value, product in content_payloads:
            directory = store / 'inbe.practices'
            payload = directory / (digest + '.zx')
            if payload.exists() and payload.read_bytes() != data:
                raise ValueError('immutable practice payload differs')
            # A paid pack is marked for the node before it can be served, so
            # Daochi only hands it out with a grant for its unlock.
            if product:
                atomic_write(directory / (digest + '.zx.product'), product.encode())
            atomic_write(payload, data)
            atomic_write(directory / (digest + '.zx.release-v2.json'),
                         (json.dumps(value, separators=(',', ':')) + '\n').encode())
        for name in NAMES:
            value = releases[name]
            directory = store / value["app_id"]
            encoded = (json.dumps(value, separators=(",", ":")) + "\n").encode()
            if len(encoded) > 65536:
                raise ValueError("release metadata exceeds the client limit")
            payload = directory / (value["artifacts"][0]["sha256"] + ".zx")
            archive = directory / f"release-{value['sequence']}.json"
            if payload.exists() and payload.read_bytes() != payloads[name]:
                raise ValueError("immutable payload does not match its hash")
            if archive.exists() and archive.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
            atomic_write(payload, payloads[name])
            atomic_write(payload.with_name(payload.name + ".release-v2.json"), encoded)
            atomic_write(archive, encoded)
            atomic_write(directory / "latest-v2.json", encoded)
    return releases


def rollout_value(percent, hours):
    """A staged release reaches buckets below percent, then everyone after hours."""
    if type(percent) is not int or not 1 <= percent <= 100 or type(hours) is not int or not 0 < hours <= 720:
        raise ValueError("rollout needs a share from 1 to 100 percent and 1 to 720 hours")
    return dict(percent=percent, hours=hours)


def stored_practice_packs(store):
    directory = store / 'inbe.practices'
    value = json.loads((directory / 'latest-v2.json').read_bytes())
    data = (directory / (value['artifacts'][0]['sha256'] + '.zx')).read_bytes()
    return catalog_from_bundle(data)


def publish(store, target, remote_store, rollout=None):
    if not re.fullmatch(r"[a-zA-Z0-9_.@-]+", target) or target.startswith("-"):
        raise ValueError("invalid SSH target")
    if not remote_store.startswith("/") or "\n" in remote_store:
        raise ValueError("Daochi package store must be an absolute path")
    # The node installs the importer independently. The upload key may be
    # restricted to this one command and this fixed store; it needs no shell,
    # SFTP access or permission to change the server's code and configuration.
    with tempfile.TemporaryDirectory(prefix="inbe-upload-") as staging:
        archive = Path(staging) / "packages.tar"
        with tarfile.open(archive, "w") as tar:
            for name in NAMES:
                app_id = "inbe" if name == "inbe" else "inbe." + name
                directory = store / app_id
                value = json.loads((directory / "latest-v2.json").read_bytes())
                payload = value["artifacts"][0]["sha256"] + ".zx"
                for filename in ("latest-v2.json", payload, payload + ".release-v2.json",
                                 f"release-{value['sequence']}.json"):
                    path = directory / filename
                    tar.add(path, arcname=str(path.relative_to(store)), recursive=False)
            for pack in stored_practice_packs(store):
                # A paid pack's marker goes too, so the node gates it; an
                # importer that cannot write markers refuses the upload.
                for suffix in ('.zx', '.zx.release-v2.json') + (('.zx.product',) if pack.get('product') else ()):
                    path = store / 'inbe.practices' / (pack['sha256'] + suffix)
                    tar.add(path, arcname=str(path.relative_to(store)), recursive=False)
            if rollout is not None:
                encoded = json.dumps(rollout_value(rollout["percent"], rollout["hours"])).encode()
                member = tarfile.TarInfo("rollout.json")
                member.size = len(encoded)
                tar.addfile(member, io.BytesIO(encoded))
        upload(archive, target, remote_store)


def stage_content_repair(store, practice, key_path, key_id, release_path, publishers_path=None):
    """Prepare an immutable resource without advancing any app release."""
    publishers = json.loads((publishers_path or ROOT / 'apps/publishers.json').read_text())
    value = json.loads(release_path.read_bytes())
    validate_release(value, 'inbe.practices', publishers)
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('publisher key must be Ed25519')
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    if not any(p['key_id'] == key_id and p['public_key'] == public and
               'inbe.practices' in p['app_ids'] for p in publishers):
        raise ValueError('content repair key must match the shipped Practices publisher')
    catalog = json.loads((ROOT / 'build/package-assets/practices/assets/practices/catalog.json').read_bytes())
    matches = [p for p in catalog['packs'] if p['practice'] == practice and not p['language']]
    if len(matches) != 1 or matches[0].get('product'):
        raise ValueError('repair requires one free base practice pack')
    pack = matches[0]
    data = (ROOT / 'build/practice-content' / (practice + '.zx')).read_bytes()
    if len(data) != pack['size'] or sha256(data).hexdigest() != pack['sha256']:
        raise ValueError('repair content differs from the app catalog')
    validate_repair_assets(data)
    value = dict(value, data_schema=1, key_id=key_id,
                 artifacts=[dict(variant='module', sha256=pack['sha256'], size=len(data))])
    value['signature'] = key.sign(signing_message(value)).hex()
    validate_release(value, 'inbe.practices', publishers)
    directory = store / 'inbe.practices'
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(directory / (pack['sha256'] + '.zx'), data)
    atomic_write(directory / (pack['sha256'] + '.zx.release-v2.json'),
                 json.dumps(value, separators=(',', ':')).encode())
    return pack['sha256']


def validate_repair_assets(data):
    """This repair is limited to Sun Salutation pictures, never paid content."""
    assets = bundle_assets(data)
    prefix = 'assets/practices/sunsalutation/'
    if not assets or any(not path.startswith(prefix) or path.startswith(
            (prefix + 'voice/', prefix + 'voice-male/')) for path in assets):
        raise ValueError('repair may contain only Sun Salutation picture resources')


def import_content_repair(entries, store, publishers):
    if len(entries) != 2:
        raise ValueError('repair must contain exactly one pack and its signature')
    payloads = [name for name in entries if re.fullmatch(r'inbe\.practices/[0-9a-f]{64}\.zx', name)]
    if len(payloads) != 1 or payloads[0] + '.release-v2.json' not in entries:
        raise ValueError('invalid content repair archive')
    name = payloads[0]
    data = entries[name]
    metadata = entries[name + '.release-v2.json']
    value = json.loads(metadata)
    validate_release(value, 'inbe.practices', publishers)
    artifact = value['artifacts'][0]
    digest = Path(name).stem
    if (value['data_schema'] != 1 or artifact['sha256'] != digest or
            artifact['size'] != len(data) or sha256(data).hexdigest() != digest):
        raise ValueError('repair content does not match its signed artifact')
    validate_repair_assets(data)
    directory = store / 'inbe.practices'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / '.publish.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (store / (name + '.product')).exists():
            raise ValueError('repair must not replace paid content')
        for filename in (name, name + '.release-v2.json'):
            target = store / filename
            if target.exists() and target.read_bytes() != entries[filename]:
                raise ValueError('repair must not replace immutable content')
        atomic_write(store / name, data)
        atomic_write(store / (name + '.release-v2.json'), metadata)


def publish_content_repair(store, digest, target, remote_store):
    if not re.fullmatch(r'[a-zA-Z0-9_.@-]+', target) or target.startswith('-'):
        raise ValueError('invalid SSH target')
    if not remote_store.startswith('/') or any(c in remote_store for c in '\n\r\0'):
        raise ValueError('invalid remote store')
    with tempfile.TemporaryDirectory(prefix='inbe-content-repair-') as temporary:
        archive = Path(temporary) / 'repair.tar'
        with tarfile.open(archive, 'w') as tar:
            for suffix in ('.zx', '.zx.release-v2.json'):
                path = store / 'inbe.practices' / (digest + suffix)
                tar.add(path, arcname=str(path.relative_to(store)), recursive=False)
        upload(archive, target, remote_store)


def verify_origin(store, origin, open_url=open_public_url):
    """Require the public node to serve the exact signed files we published."""
    parsed = urlsplit(origin)
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/") or
            (parsed.scheme != "https" and not
             (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")))):
        raise ValueError("verification origin must be HTTPS, or a loopback HTTP test node")
    origin = origin.rstrip("/")
    for name in NAMES:
        app_id = "inbe" if name == "inbe" else "inbe." + name
        expected = json.loads((store / app_id / "latest-v2.json").read_bytes())
        route = origin + "/api/v2/packages/" + app_id
        # Bucket 0 receives a staged release first. Hosts that run ZX ask with
        # format=zx; without it the node offers only legacy .zib releases.
        with open_url(route + "/latest?bucket=0&format=zx", timeout=30) as response:
            encoded = response.read(65537)
        if len(encoded) > 65536 or json.loads(encoded) != expected:
            raise ValueError(f"{app_id}: public release metadata differs from the signed publication")
        artifact = expected["artifacts"][0]
        digest = artifact["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not 8 <= artifact["size"] <= 64 * 1024 * 1024:
            raise ValueError(f"{app_id}: invalid staged artifact")
        checksum = sha256()
        size = 0
        with open_url(route + "/" + digest + ".zx", timeout=30) as response:
            while True:
                block = response.read(65536)
                if not block:
                    break
                size += len(block)
                if size > artifact["size"]:
                    raise ValueError(f"{app_id}: public package exceeds its signed size")
                checksum.update(block)
        if size != artifact["size"] or checksum.hexdigest() != digest:
            raise ValueError(f"{app_id}: public package hash or size differs from the signed publication")
    for pack in stored_practice_packs(store):
        route = origin + '/api/v2/packages/inbe.practices/' + pack['sha256'] + '.zx'
        # The node serves a paid pack only with its grant, so the public
        # route must refuse it.
        if pack.get('product'):
            try:
                open_url(route, timeout=30).close()
            except HTTPError as error:
                if error.code == 403:
                    continue
                raise
            raise ValueError('paid practice content is public without a grant')
        checksum = sha256()
        size = 0
        with open_url(route, timeout=30) as response:
            while True:
                block = response.read(65536)
                if not block:
                    break
                size += len(block)
                if size > pack['size']:
                    raise ValueError('public practice content exceeds its catalog size')
                checksum.update(block)
        if size != pack['size'] or checksum.hexdigest() != pack['sha256']:
            raise ValueError('public practice content differs from its signed catalog')
    print("Verified public signed metadata, app packages and practice content")


def published_changes(store, origin, open_url=open_public_url):
    """Compare the staged releases with the ones the public node serves.

    Returns the apps with a new version and the apps whose package changed
    without one. Signing is deterministic, so an unchanged package stages
    exactly the release the node already serves.
    """
    origin = origin.rstrip("/")
    advanced = []
    unversioned = []
    for name in NAMES:
        app_id = "inbe" if name == "inbe" else "inbe." + name
        staged = json.loads((store / app_id / "latest-v2.json").read_bytes())
        try:
            with open_url(origin + "/api/v2/packages/" + app_id + "/latest?bucket=0&format=zx",
                          timeout=30) as response:
                encoded = response.read(65537)
        except HTTPError as error:
            if error.code != 404:
                raise
            advanced.append(app_id)
            continue
        if len(encoded) > 65536:
            raise ValueError(f"{app_id}: public release metadata is too large")
        served = json.loads(encoded)
        if served == staged:
            continue
        if staged["sequence"] > served["sequence"] and version_tuple(staged) > version_tuple(served):
            advanced.append(app_id)
        else:
            unversioned.append(app_id)
    return advanced, unversioned


def import_archive(archive, store, publishers_path=None):
    """Node-side merge. Daochi still checks registry/key status on every GET."""
    publishers = json.loads((publishers_path or ROOT / "apps/publishers.json").read_text())
    ids = BUNDLED_IDS
    entries = {}
    total = 0
    rollout = None
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if member.name == "rollout.json" and member.isfile() and member.size <= 1024 and rollout is None:
                rollout = json.loads(tar.extractfile(member).read())
                if not isinstance(rollout, dict) or set(rollout) != {"percent", "hours"}:
                    raise ValueError("invalid rollout")
                rollout = rollout_value(rollout["percent"], rollout["hours"])
                continue
            parts = Path(member.name).parts
            if len(parts) != 2 or (parts[0] not in ids and not node_app_id(parts[0])) or \
                    not member.isfile() or member.size > 64 * 1024 * 1024:
                raise ValueError("invalid archive member")
            if member.name in entries:
                raise ValueError("duplicate archive member")
            total += member.size
            # Four files per app, and up to 65 practice packs, each with its
            # release and, when paid, its product marker.
            if len(entries) >= 7 * 4 + 65 * 3 or total > 1024 * 1024 * 1024:
                raise ValueError("archive exceeds the release size limit")
            entries[member.name] = tar.extractfile(member).read()
    # The node accepts archives built before and after Leaderboard became an
    # app, so the importer and the app can be updated in either order.
    present = {name.split("/")[0] for name in entries}
    if present == {'inbe.practices'}:
        if rollout is not None:
            raise ValueError('content repair cannot change rollout')
        import_content_repair(entries, store, publishers)
        archive.unlink()
        archive.parent.rmdir()
        return
    if len(present) == 1 and node_app_id(next(iter(present))):
        if rollout is not None:
            raise ValueError("an app the node offers is published to everyone at once")
        import_node_app(entries, store, publishers, next(iter(present)))
        archive.unlink()
        archive.parent.rmdir()
        return
    if present != ids and present != ids - {"inbe.leaderboard"}:
        raise ValueError("archive must contain the root and every cell")
    with ExitStack() as stack:
        releases = {}
        for app_id in sorted(present):
            directory = store / app_id
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock = stack.enter_context((directory / ".publish.lock").open("a+b"))
            fcntl.flock(lock, fcntl.LOCK_EX)
            encoded = entries[f"{app_id}/latest-v2.json"]
            if len(encoded) > 65536:
                raise ValueError("metadata is too large")
            value = json.loads(encoded)
            validate_release(value, app_id, publishers)
            artifact = value["artifacts"][0]
            data = entries[f"{app_id}/{artifact['sha256']}.zx"]
            if artifact["size"] != len(data) or sha256(data).hexdigest() != artifact["sha256"]:
                raise ValueError("payload hash mismatch")
            if not data.startswith(b"ZX\0\0"):
                raise ValueError("payload is not a ZX bundle")
            current = directory / "latest-v2.json"
            old = None
            if current.exists():
                old = json.loads(current.read_bytes())
                if old != value and (old["sequence"] >= value["sequence"] or
                        tuple(map(int, old["version"].split("."))) >=
                        tuple(map(int, value["version"].split(".")))):
                    raise ValueError("release must advance the installed version and sequence")
            archived = directory / f"release-{value['sequence']}.json"
            if archived.exists() and archived.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
            releases[app_id] = (value, encoded, data, old != value)
        root = releases["inbe"]
        content_payloads = []
        expected_entries = set()
        for app_id, (value, encoded, data, _) in releases.items():
            digest = value['artifacts'][0]['sha256']
            expected_entries.update((f'{app_id}/latest-v2.json', f'{app_id}/{digest}.zx',
                f'{app_id}/{digest}.zx.release-v2.json', f"{app_id}/release-{value['sequence']}.json"))
        for pack in catalog_from_bundle(releases['inbe.practices'][2]):
            path = 'inbe.practices/' + pack['sha256'] + '.zx'
            expected_entries.update((path, path + '.release-v2.json'))
            product = pack.get('product', '')
            if product:
                expected_entries.add(path + '.product')
                if entries.get(path + '.product') != product.encode():
                    raise ValueError('paid practice content lacks its product marker')
            data = entries[path]
            encoded = entries[path + '.release-v2.json']
            value = json.loads(encoded)
            validate_release(value, 'inbe.practices', publishers)
            if (value['data_schema'] != 1 or value['artifacts'][0]['sha256'] != pack['sha256'] or
                    value['artifacts'][0]['size'] != pack['size'] or len(data) != pack['size'] or
                    sha256(data).hexdigest() != pack['sha256']):
                raise ValueError('practice content differs from its signed catalog')
            bundle_assets(data)
            content_payloads.append((path, data, encoded, product))
        if set(entries) - expected_entries:
            raise ValueError('archive contains unreferenced content')
        for dependency in root[0]["dependencies"]:
            child, _, payload, _ = releases[dependency["app_id"]]
            artifact = child["artifacts"][0]
            if dependency != dict(app_id=child["app_id"], version=child["version"],
                                  sha256=artifact["sha256"], size=artifact["size"]) or root[2].count(payload) != 1:
                raise ValueError("root does not contain its exact signed cell dependency")
        # Content precedes both the harness and the root that references it.
        for path, data, encoded, product in content_payloads:
            target = store / path
            if target.exists() and target.read_bytes() != data:
                raise ValueError('immutable practice content differs')
            # The marker precedes the pack, so Daochi never serves it ungated.
            if product:
                atomic_write(store / (path + '.product'), product.encode())
            atomic_write(target, data)
            atomic_write(store / (path + '.release-v2.json'), encoded)
        # Dependencies go first. Publishing the root is the final step.
        for app_id in sorted(present, key=lambda value: value == "inbe"):
            value, encoded, data, changed = releases[app_id]
            directory = store / app_id
            payload = directory / (value["artifacts"][0]["sha256"] + ".zx")
            archived = directory / f"release-{value['sequence']}.json"
            if archived.exists() and archived.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
            atomic_write(payload, data)
            atomic_write(payload.with_name(payload.name + ".release-v2.json"), encoded)
            atomic_write(archived, encoded)
            atomic_write(directory / "latest-v2.json", encoded)
            # Daochi holds a staged release back from the other buckets until
            # it expires. A new full release or a full rollout ends staging.
            staged = directory / "rollout.json"
            if rollout is not None and rollout["percent"] < 100 and changed:
                until = int(time.time()) + rollout["hours"] * 3600
                atomic_write(staged, json.dumps(dict(sequence=value["sequence"], percent=rollout["percent"],
                                                     until=until)).encode())
            elif changed or (rollout is not None and rollout["percent"] == 100):
                staged.unlink(missing_ok=True)
            write_history(directory, app_id, publishers)
    archive.unlink()
    archive.parent.rmdir()


def receive_archive(store, publishers_path):
    if shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND", "")) != ["inbe-packages", str(store)]:
        raise ValueError("upload key permits only publication to its configured package store")
    with tempfile.TemporaryDirectory(prefix="inbe-receive-") as directory:
        archive = Path(directory) / "packages.tar"
        maximum = 7 * 64 * 1024 * 1024 + 1024 * 1024
        total = 0
        with archive.open("wb") as output:
            while True:
                block = sys.stdin.buffer.read(65536)
                if not block:
                    break
                total += len(block)
                if total > maximum:
                    raise ValueError("upload exceeds the release size limit")
                output.write(block)
        import_archive(archive, store, publishers_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--key-id")
    parser.add_argument("--ssh-target")
    parser.add_argument("--remote-store")
    parser.add_argument("--verify-origin", help="verify served release metadata and bytes after publishing")
    parser.add_argument("--import-archive", type=Path)
    parser.add_argument("--receive-archive", action="store_true")
    parser.add_argument("--publishers", type=Path, help="node-owned public publisher pins")
    parser.add_argument("--rollout", type=int, help="publish changed releases to this share of devices first")
    parser.add_argument("--rollout-hours", type=int, default=24, help="then to every device after these hours")
    parser.add_argument('--repair-content', choices=['sunsalutation'],
                        help='restore only the missing Sun Salutation picture pack')
    parser.add_argument('--repair-release', type=Path, help='existing signed Practices metadata for a content repair')
    parser.add_argument("--write-history", action="store_true",
                        help="on the node: list each app's newest three releases for rollback")
    node_release.add_node_app_arguments(parser)
    args = parser.parse_args()
    try:
        if node_release.publish_from_arguments(args, parser, ROOT):
            return
        if args.write_history:
            if not args.publishers:
                parser.error("--write-history needs the node's --publishers")
            write_histories(args.store, args.publishers)
            print("Release histories written")
            return
        if args.repair_content:
            if not args.key or not args.key_id or not args.repair_release or args.rollout is not None:
                parser.error('content repair needs --key, --key-id and --repair-release, without --rollout')
            digest = stage_content_repair(args.store, args.repair_content, args.key,
                                          args.key_id, args.repair_release, args.publishers)
            if args.ssh_target:
                if not args.remote_store or not args.verify_origin:
                    parser.error('repair publication requires --remote-store and --verify-origin')
                origin = args.verify_origin.rstrip('/')
                parsed = urlsplit(origin)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
                    raise ValueError('repair verification requires an HTTPS origin')
                publish_content_repair(args.store, digest, args.ssh_target, args.remote_store)
                expected = (args.store / 'inbe.practices' / (digest + '.zx')).read_bytes()
                with open_public_url(origin + '/api/v2/packages/inbe.practices/' + digest + '.zx', 30) as response:
                    if response.read(len(expected) + 1) != expected:
                        raise ValueError('public repair differs from the app catalog')
            print('Sun Salutation picture pack repaired' if args.ssh_target else 'Sun Salutation picture repair staged')
            return
        if args.receive_archive:
            if not args.publishers:
                parser.error("--publishers is required for the restricted upload receiver")
            receive_archive(args.store, args.publishers)
        elif args.import_archive:
            import_archive(args.import_archive, args.store, args.publishers)
        else:
            if not args.key or not args.key_id:
                parser.error("--key and --key-id are required")
            stage(args.store, args.key, args.key_id)
            if args.ssh_target:
                if not args.remote_store:
                    parser.error("--remote-store is required with --ssh-target")
                if args.verify_origin:
                    advanced, unversioned = published_changes(args.store, args.verify_origin)
                    # A package that changed without a new version waits for
                    # its next version; that is not a failure. The node
                    # accepts every app together or none, so a new version
                    # that ships beside an unversioned change waits too: the
                    # release, whose ./update_version.sh versions every
                    # package, publishes them together.
                    if unversioned and advanced:
                        print("::notice title=App packages::Waiting for the next release: " +
                              ", ".join(advanced) + " ships together with " + ", ".join(unversioned) +
                              ", which changed without a new version")
                        return
                    if unversioned:
                        print("::notice title=App packages::Not published: " + ", ".join(unversioned) +
                              " changed without a new version and will publish with the next one")
                        return
                    if not advanced:
                        print("Every package is already published")
                        return
                rollout = None if args.rollout is None else rollout_value(args.rollout, args.rollout_hours)
                publish(args.store, args.ssh_target, args.remote_store, rollout)
            if args.verify_origin:
                verify_origin(args.store, args.verify_origin)
        print("Inbe package releases published" if args.ssh_target or args.import_archive or args.receive_archive else "Inbe package releases staged")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Package publication failed: {error}\n")


if __name__ == "__main__":
    main()
