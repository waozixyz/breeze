#!/usr/bin/env python3
"""Put every practice pack this build needs on Waozi's node.

The app downloads each practice and narration pack by its SHA-256 from the
node, so a build installed on a phone only works when its packs are there.
Pushed builds get theirs from the App packages workflow; a local build does
not. The owner allows uploading practice packs at any time (never app
releases or latest-v2.json): this signs the built packs with the Inbe
publisher key, uploads only those the node does not hold yet (a paid pack's
product marker first, so it is never served without a grant) and checks
that each one is served afterwards. Sun Salutation, the largest pack, is then
downloaded from the node in full and checked, so every phone build tests
that practices really download.

Run after `make` or a phone build, from the repository root:
    python3 scripts/upload-practice-packs.py

Limit staging, signing and transport to exact built pack filenames:
    python3 scripts/upload-practice-packs.py --pack astral_projection.pt --pack guide.pt
The existing --content option selects base content only.
"""
import argparse
from datetime import datetime
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NODE = "https://api.waozi.xyz/api/v2/packages/inbe.practices/"
TARGET = "root@107.175.0.107"
STORE = "/var/lib/daochi/daochi.db.packages"
KEY = ROOT / "backup/package-publisher/2026-10/publisher.pem"
KEY_ID = "inbe-2026-10"
RECEIPT = ROOT / "backup/practice-packs/uploads.txt"
# The node's proxy refuses Python's default user agent with 403, which would
# read as a paid pack that is present.
HEADERS = {"User-Agent": "InnerBreeze-practice-packs/1"}

spec = importlib.util.spec_from_file_location("package_release", ROOT / "scripts/package-release.py")
package_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_release)


def served(digest, timeout=30):
    """The node's status for a pack: 200 served, 403 paid and present, 404 missing."""
    request = urllib.request.Request(NODE + digest + ".zx", method="HEAD", headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def matches(digest, size, timeout=120):
    request = urllib.request.Request(NODE + digest + ".zx", headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        checksum = sha256()
        count = 0
        while block := response.read(65536):
            count += len(block)
            if count > size:
                return False
            checksum.update(block)
    return count == size and checksum.hexdigest() == digest


def pack_identifier(pack):
    """The built filename without .zx, including its language and voice."""
    return (pack['practice'] + ('.' + pack['language'] if pack['language'] else '') +
            ('.' + pack['voice'] if pack.get('voice') else ''))


def select_packs(catalog, identifiers=None, content=None):
    if identifiers is not None:
        known = {pack_identifier(pack) for pack in catalog}
        unknown = set(identifiers) - known
        if not identifiers or unknown or not all(identifiers):
            raise ValueError('unknown or empty pack selection: ' + ', '.join(sorted(unknown)))
        return [pack for pack in catalog if pack_identifier(pack) in set(identifiers)]
    return [pack for pack in catalog if not content or
            (pack['practice'] in content and not pack['language'])]


def stage_selected_packs(store, packs):
    """Sign only the selected immutable content; never stage app releases."""
    key = package_release.serialization.load_pem_private_key(KEY.read_bytes(), password=None)
    if not isinstance(key, package_release.Ed25519PrivateKey):
        raise ValueError('publisher key must be Ed25519')
    publishers = json.loads((ROOT / 'apps/publishers.json').read_text())
    public_key = key.public_key().public_bytes(package_release.serialization.Encoding.Raw,
        package_release.serialization.PublicFormat.Raw).hex()
    trusted = package_release.node_release.trusted_pin(publishers, KEY_ID, 'inbe.practices')
    if trusted is None or trusted['public_key'] != public_key:
        raise ValueError('signing key must match the public key shipped in apps/publishers.json')
    versions = json.loads((ROOT / 'apps/versions.json').read_text())
    component = versions['apps']['practices']
    if component['id'] != 'inbe.practices':
        raise ValueError('invalid Practices package identity')
    directory = store / 'inbe.practices'
    directory.mkdir(parents=True, exist_ok=True)
    for pack in packs:
        digest = pack['sha256']
        target = directory / (digest + '.zx')
        shutil.copyfile(ROOT / 'build/practice-content' / (pack_identifier(pack) + '.zx'), target)
        with target.open('rb') as stream:
            checksum = sha256()
            while block := stream.read(65536):
                checksum.update(block)
        if target.stat().st_size != pack['size'] or checksum.hexdigest() != digest:
            raise ValueError('practice content differs from its signed catalog')
        value = dict(app_id=component['id'], sequence=component['sequence'],
                     version=component['version'], runtime='kryon-app-v1',
                     host_api=component.get('host_api', versions['host_api']),
                     module_api=versions['module_api'], data_schema=1, key_id=KEY_ID,
                     artifacts=[dict(variant='module', sha256=digest, size=pack['size'])],
                     dependencies=[])
        value['signature'] = key.sign(package_release.signing_message(value)).hex()
        package_release.validate_release(value, 'inbe.practices', publishers)
        package_release.atomic_write(directory / (digest + '.zx.release-v2.json'),
            (json.dumps(value, separators=(',', ':')) + chr(10)).encode())
        if pack.get('product'):
            package_release.atomic_write(directory / (digest + '.zx.product'), pack['product'].encode())


def sun_salutation_downloads(packs):
    """Downloads the Sun Salutation pack this build lists and checks its bytes."""
    pack = next(pack for pack in packs if pack["practice"] == "sunsalutation" and not pack["language"])
    started = time.monotonic()
    if not matches(pack["sha256"], pack["size"]):
        print("Sun Salutation does not download exactly from the node", file=sys.stderr)
        return False
    print(f"Sun Salutation downloads from the node: {pack['size'] / 1e6:.1f} MB "
          f"in {time.monotonic() - started:.1f} s")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only report packs missing on the node")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--content", action="append",
                        choices=json.loads((ROOT / "apps/practice/content.json").read_text())["practices"],
                        help="limit this attempt to the named practice's content pack; repeat for another practice")
    selection.add_argument('--pack', action='append',
                           help='exact catalog filename without .zx, e.g. astral_projection.pt, guide.pt or taichi.en.male; repeat for another pack')
    args = parser.parse_args()
    practices = (ROOT / 'build/apps/practices.zx').read_bytes()
    try:
        listed = select_packs(package_release.catalog_from_bundle(practices), args.pack, args.content)
    except ValueError as error:
        parser.error(str(error))
    sun_content = any(pack['practice'] == 'sunsalutation' and not pack['language'] for pack in listed)
    with tempfile.TemporaryDirectory(prefix="inbe-practice-packs-", dir=ROOT / "build") as scratch:
        store = Path(scratch)
        # Availability checks need only the catalog, not a signing key or any
        # unrelated app bundle. Installation must also work on build hosts
        # that do not hold the private publisher key.
        if args.check:
            missing = []
            for pack in listed:
                status = served(pack['sha256'])
                expected = 403 if pack.get('product') else 200
                if status == 404:
                    missing.append(pack)
                elif status != expected:
                    raise SystemExit(f"node answered {status} for practice pack {pack_identifier(pack)}")
            print(f"{len(listed)} packs built, {len(missing)} missing on the node")
            if missing:
                for pack in missing:
                    print(f"missing: {pack_identifier(pack)}", file=sys.stderr)
                return 1
            if args.pack is not None:
                for pack in listed:
                    if not pack.get('product') and not matches(pack['sha256'], pack['size']):
                        raise SystemExit(f"pack {pack['sha256']} is not served exactly")
            return 0 if not sun_content or sun_salutation_downloads(listed) else 1
        # Only content is being delivered. Requiring a complete, matching
        # root and every unrelated app here made local content repair fail
        # before it could upload the practice the installed build requests.
        stage_selected_packs(store, listed)
        directory = store / "inbe.practices"
        # Only selected catalog content can reach the transport.
        catalog = {pack["sha256"] for pack in listed}
        packs = sorted(directory / (digest + ".zx") for digest in catalog)
        missing = []
        for path in packs:
            digest = path.stem
            gated = (directory / (digest + ".zx.product")).exists()
            status = served(digest)
            if status == 404:
                missing.append(path)
            elif status != (403 if gated else 200):
                raise SystemExit(f"node answered {status} for {'paid' if gated else 'free'} pack {digest}")
        print(f"{len(packs)} packs built, {len(missing)} missing on the node")
        if not missing:
            if args.pack is not None:
                for path in packs:
                    if not (directory / (path.stem + '.zx.product')).exists() and not matches(path.stem, path.stat().st_size):
                        raise SystemExit(f'pack {path.stem} is not served exactly')
            return 0 if not sun_content or sun_salutation_downloads(listed) else 1
        archive = io.BytesIO()
        members = []
        with tarfile.open(fileobj=archive, mode="w") as tar:
            for path in missing:
                for suffix in (".zx.product", ".zx", ".zx.release-v2.json"):
                    member = directory / (path.stem + suffix)
                    if member.exists():
                        info = tar.gettarinfo(str(member), arcname="inbe.practices/" + member.name)
                        info.uid = info.gid = 0
                        info.uname = info.gname = "root"
                        info.mode = 0o600
                        with member.open("rb") as handle:
                            tar.addfile(info, handle)
                        members.append(info.name)
        # Extract only into the practices folder, never over a file that is
        # already there: packs are immutable once served.
        permissions = ' '.join(shlex.quote(name) for name in members)
        command = ("set -e; cd " + STORE + " && tar -x --keep-old-files --no-same-permissions "
                   "--wildcards 'inbe.practices/*' -f - && chmod 600 " + permissions)
        subprocess.run(["ssh", "-o", "BatchMode=yes", TARGET, command],
                       input=archive.getvalue(), check=True)
        lines = []
        for path in (packs if args.pack is not None else missing):
            digest = path.stem
            gated = (directory / (digest + ".zx.product")).exists()
            if gated:
                if served(digest) != 403:
                    raise SystemExit(f"paid pack {digest} is not withheld by the node")
            elif not matches(digest, path.stat().st_size):
                raise SystemExit(f"pack {digest} is not served exactly")
            if path in missing:
                lines.append(f"{digest} {path.stat().st_size} {'paid' if gated else 'free'}")
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPT.open("a") as receipt:
            receipt.write(datetime.now().astimezone().isoformat(timespec="seconds") +
                          f" uploaded {len(lines)} practice packs\n")
            receipt.writelines(line + "\n" for line in lines)
        print("\n".join(lines))
        print(f"Uploaded {len(lines)} practice packs; each is served")
        if sun_content and not sun_salutation_downloads(listed):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
