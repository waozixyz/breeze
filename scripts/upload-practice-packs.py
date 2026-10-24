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
"""
import argparse
from datetime import datetime
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
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
        data = response.read(size + 1)
    return len(data) == size and sha256(data).hexdigest() == digest


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
    parser.add_argument("--content", action="append",
                        choices=json.loads((ROOT / "apps/practice/content.json").read_text())["practices"],
                        help="limit this attempt to the named practice's content pack; repeat for another practice")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="inbe-practice-packs-") as scratch:
        store = Path(scratch)
        # Signs every app release into the scratch store; only the practice
        # packs from it are ever uploaded.
        package_release.stage(store, KEY, KEY_ID)
        directory = store / "inbe.practices"
        # The store also holds the Practice app's own bundle under this app
        # ID; only the content packs its catalog names are uploaded.
        practices = (ROOT / "build/cells/practices.zx").read_bytes()
        listed = package_release.catalog_from_bundle(practices)
        if args.content:
            listed = [pack for pack in listed if pack["practice"] in args.content and not pack["language"]]
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
        if args.check or not missing:
            if missing and args.check:
                return 1
            return 0 if not any(pack["practice"] == "sunsalutation" for pack in listed) or sun_salutation_downloads(listed) else 1
        archive = io.BytesIO()
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
        # Extract only into the practices folder, never over a file that is
        # already there: packs are immutable once served.
        command = ("set -e; cd " + STORE + " && tar -x --keep-old-files --no-same-permissions "
                   "--wildcards 'inbe.practices/*' -f - && chmod 600 inbe.practices/*.zx*")
        subprocess.run(["ssh", "-o", "BatchMode=yes", TARGET, command],
                       input=archive.getvalue(), check=True)
        lines = []
        for path in missing:
            digest = path.stem
            gated = (directory / (digest + ".zx.product")).exists()
            if gated:
                if served(digest) != 403:
                    raise SystemExit(f"paid pack {digest} is not withheld by the node")
            elif not matches(digest, path.stat().st_size):
                raise SystemExit(f"pack {digest} is not served exactly")
            lines.append(f"{digest} {path.stat().st_size} {'paid' if gated else 'free'}")
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPT.open("a") as receipt:
            receipt.write(datetime.now().astimezone().isoformat(timespec="seconds") +
                          f" uploaded {len(lines)} practice packs\n")
            receipt.writelines(line + "\n" for line in lines)
        print("\n".join(lines))
        print(f"Uploaded {len(lines)} practice packs; each is served")
        if any(pack["practice"] == "sunsalutation" for pack in listed) and not sun_salutation_downloads(listed):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
