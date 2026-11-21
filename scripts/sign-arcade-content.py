#!/usr/bin/env python3
"""Sign immutable game lookups for the exact Arcade catalog shipped in this tree.

The publisher key stays in the established CI secret. This produces only
per-digest descriptors, never an app release or a latest/history pointer.
"""
import argparse
import importlib.util
import json
import os
from hashlib import sha256
from pathlib import Path
import re

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from practice_content import bundle_assets

ROOT = Path(__file__).resolve().parents[1]
APP = "inbe.arcade"


def load_release_api(path):
    spec = importlib.util.spec_from_file_location("arcade_release_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def catalog_entries(root, expected_digest):
    declaration = json.loads((root / "apps/bundled.json").read_text())["arcade"]
    if declaration["id"] != APP or declaration["path"] != "apps/bundled/arcade.zx":
        raise ValueError("unexpected bundled Arcade identity or path")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest) or declaration["sha256"] != expected_digest:
        raise ValueError("bundled Arcade differs from the requested catalog")
    path = root / declaration["path"]
    if path.is_symlink() or not 8 <= path.stat().st_size <= 65536:
        raise ValueError("Arcade catalog must be a small regular bundle")
    data = path.read_bytes()
    if len(data) != declaration["bytes"] or sha256(data).hexdigest() != expected_digest:
        raise ValueError("Arcade catalog bytes differ from their declaration")
    catalog = json.loads(bundle_assets(data)["assets/apps/catalog.json"])
    if catalog.get("schema") != 1 or catalog.get("id") != APP:
        raise ValueError("unexpected Arcade catalog identity")
    children = catalog.get("children")
    if not isinstance(children, list) or not 1 <= len(children) <= 16:
        raise ValueError("invalid Arcade game list")
    entries = children + [catalog["art"]]
    digests = set()
    for entry in entries:
        digest, size = entry.get("sha256"), entry.get("bytes")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid Arcade content digest")
        if type(size) is not int or not 8 <= size <= 64 * 1024 * 1024:
            raise ValueError("invalid Arcade content size")
        if digest in digests:
            raise ValueError("duplicate Arcade content digest")
        digests.add(digest)
    return declaration, entries


def sign(root, expected_digest, key_bytes, key_id, output, api):
    declaration, entries = catalog_entries(root, expected_digest)
    publishers = json.loads((root / "apps/publishers.json").read_text())
    key = serialization.load_pem_private_key(key_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("publisher key must be Ed25519")
    public_key = key.public_key().public_bytes(serialization.Encoding.Raw,
                                              serialization.PublicFormat.Raw).hex()
    pin = api.trusted_pin(publishers, key_id, APP)
    if pin is None or pin["public_key"] != public_key or declaration["key_id"] != key_id:
        raise ValueError("publisher key does not match the installed Arcade trust pin")
    versions = json.loads((root / "apps/versions.json").read_text())
    descriptors = {}
    for entry in entries:
        value = dict(app_id=APP, sequence=declaration["sequence"], version=declaration["version"],
                     runtime="kryon-app-v1", host_api=declaration["host_api"],
                     module_api=versions["module_api"], data_schema=0, key_id=key_id,
                     artifacts=[dict(variant="module", sha256=entry["sha256"], size=entry["bytes"])],
                     dependencies=[])
        value["signature"] = key.sign(api.signing_message(value)).hex()
        api.validate_release(value, APP, publishers)
        descriptors[entry["sha256"] + ".zx.release-v2.json"] = (
            json.dumps(value, separators=(",", ":")) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or any(output.iterdir()):
        raise ValueError("signing output must be an empty regular directory")
    for name, encoded in descriptors.items():
        with (output / name).open("xb") as destination:
            destination.write(encoded)
    print(f"Signed {len(descriptors)} catalog-bound content descriptors", flush=True)
    return descriptors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-sha256", required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-api", type=Path, default=ROOT / "build/packages/apps/scripts/node_release.py")
    args = parser.parse_args()
    key = os.environ.get("INBE_PACKAGE_SIGNING_KEY")
    if not key:
        raise SystemExit("the established package signing secret is required")
    sign(ROOT, args.catalog_sha256, key.encode(), args.key_id, args.output,
         load_release_api(args.release_api))


if __name__ == "__main__":
    main()
