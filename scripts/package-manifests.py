#!/usr/bin/env python3
"""Prepare signed node registrations without replacing existing account scopes.

The node operator supplies its registry approval key. The package publisher
key alone cannot authorize registration. Output contains public manifests and
signatures only; neither private key is copied to the node or the output.

--app NAME prepares one app, also from another project's ledger
(--app-ledger, such as Arcade's inbe.arcade). --suspend prepares that app's
suspension: the node then stops listing and serving it, and devices that
installed it keep their copy. A suspension needs a manifest sequence above
the node's, so an older approval cannot undo it.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"inbe": "Inner Breeze", "habits": "Habits", "practices": "Practices",
         "lists": "Lists", "diary": "Diary", "lumi": "Lumi",
         "leaderboard": "Leaderboard"}
# Declaration order is part of Daochi's Go JSON signature contract.
FIELDS = ("manifest_version", "manifest_sequence", "app_id", "display_name", "description",
          "homepage_url", "source_url", "status", "expires_at", "lan_only",
          "lan_networks", "registration_node_id", "app_schema_version",
          "min_supported_client_version", "current_client_version",
          "compatibility_until", "keys", "collections", "capabilities",
          "features", "legacy_protocols", "token_policies")
CHILD_FIELDS = {
    "keys": ("key_id", "algorithm", "public_key", "purpose", "status", "expires_at", "created_at"),
    "collections": ("app_id", "collection_prefix", "visibility", "schema_version", "description", "created_at"),
    "features": ("id", "collections", "requires_signed_tx", "description"),
    "legacy_protocols": ("name", "version", "status", "valid_until"),
    "token_policies": ("asset_id", "permission", "status", "legacy_unsigned_until"),
}
REQUIRED = {"keys": {"key_id", "algorithm", "public_key"},
            "collections": {"collection_prefix", "visibility"},
            "features": {"id"}, "legacy_protocols": {"name", "status", "valid_until"},
            "token_policies": {"asset_id", "permission"}}


def private_key(path):
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("registration requires an Ed25519 key")
    return key


def public_hex(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,
                                         serialization.PublicFormat.Raw).hex()


def canonical_bytes(manifest):
    # Match encoding/json, including HTML and line-separator escaping.
    text = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    for character in "<>&\u2028\u2029":
        text = text.replace(character, "\\u%04x" % ord(character))
    return text.encode("utf-8")


def manifest_for(component, existing, key_id, public):
    if existing and (existing.get("app_id") != component["id"] or
                     existing.get("status") != "active"):
        raise ValueError("refusing to replace an unrelated or suspended registration")
    if existing.get("lan_only") or existing.get("registration_node_id"):
        raise ValueError("refusing to change a node-restricted app registration")
    values = {field: existing[field] for field in FIELDS if existing.get(field)}
    values.update(app_id=component["id"], display_name=NAMES.get(component["name"]) or component["title"],
                  homepage_url="https://inbe.waozi.xyz/",
                  source_url=component.get("source_url", "https://github.com/waozixyz/inbe"), status="active",
                  current_client_version=component["version"])
    keys = [dict(key) for key in existing.get("keys", [])]
    old_key = next((key for key in keys if key["key_id"] == key_id), None)
    if old_key and (old_key.get("public_key") != public or old_key.get("status", "active") != "active"):
        raise ValueError("publisher key ID is occupied or revoked; choose a new key ID")
    if old_key is None:
        keys.append(dict(key_id=key_id, algorithm="ed25519", public_key=public,
                         purpose="signing", status="active"))
    values["keys"] = keys
    for field, fields in CHILD_FIELDS.items():
        if field not in values:
            continue
        values[field] = [{key: item[key] for key in fields
                          if key in item and (item[key] or key in REQUIRED[field])}
                         for item in values[field]]
    previous_version = existing.get("manifest_version", 0)
    if type(previous_version) is not int or previous_version not in (0, 1):
        raise ValueError("unsupported previous manifest version")
    # This is the registry protocol version, not an app release counter.
    # Client versions and signed package sequences advance independently.
    values["manifest_version"] = 1
    return {key: values[key] for key in FIELDS if key in values}


def suspension_for(app_id, existing, key_id, public, sequence):
    """The node's registration of app_id, unchanged except suspended.

    Daochi keeps the manifest with the highest sequence, so the suspension
    must name one above the node's: a replayed older approval cannot list the
    app again.
    """
    if not existing or existing.get("app_id") != app_id:
        raise ValueError(f"{app_id} is not registered on the node")
    if existing.get("status") != "active":
        raise ValueError(f"{app_id} is not active on the node")
    if type(sequence) is not int or sequence < 1:
        raise ValueError("a suspension needs a manifest sequence of at least 1")
    if existing.get("lan_only") or existing.get("registration_node_id"):
        raise ValueError("refusing to change a node-restricted app registration")
    keys = existing.get("keys", [])
    if not any(key.get("key_id") == key_id and key.get("public_key") == public and
               key.get("status", "active") == "active" for key in keys):
        raise ValueError("the publisher key must already sign this registration")
    values = {field: existing[field] for field in FIELDS if existing.get(field)}
    for field, fields in CHILD_FIELDS.items():
        if field not in values:
            continue
        values[field] = [{key: item[key] for key in fields
                          if key in item and (item[key] or key in REQUIRED[field])}
                         for item in values[field]]
    if existing.get("manifest_version", 0) not in (0, 1):
        raise ValueError("unsupported previous manifest version")
    values.update(manifest_version=1, manifest_sequence=sequence, status="suspended")
    return {key: values[key] for key in FIELDS if key in values}


def signed_registration(manifest, publisher, authority):
    encoded = canonical_bytes(manifest)
    digest = sha256(encoded).hexdigest()
    return dict(manifest=manifest,
                manifest_signature=publisher.sign(b"daochi-app-manifest-v1\n" + encoded).hex(),
                approval_signature=authority.sign(
                    f"daochi-app-approval-v1\n{manifest['app_id']}\n{digest}\n".encode()).hex())


def ledger_components(versions, ledger_path, only):
    """The apps to prepare: Inbe's own, or one app from its owning ledger."""
    components = list(versions["apps"].items()) + list(versions.get("node_apps", {}).items())
    if ledger_path is not None:
        owned = json.loads(Path(ledger_path).read_text()).get("node_apps", {})
        # Games inside a collection keep their own IDs and are not node apps.
        components = [(name, component) for name, component in owned.items()
                      if component.get("id") == "inbe." + name]
    if only is None:
        return components
    chosen = [(name, component) for name, component in components if name == only]
    if not chosen:
        raise ValueError(f"{only} is not an app in this ledger")
    return chosen


def registrations(origin, key_path, approval_path, key_id, output, open_url=urlopen,
                  ledger_path=None, only=None, suspend=False, manifest_sequence=0):
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" and not (parsed.scheme == "http" and
            parsed.hostname in ("127.0.0.1", "localhost", "::1"))) or not parsed.hostname or \
            parsed.username or parsed.password or parsed.path not in ("", "/") or \
            parsed.query or parsed.fragment:
        raise ValueError("registry origin must be HTTPS or local HTTP")
    publisher = private_key(key_path)
    authority = private_key(approval_path)
    public = public_hex(publisher)
    pins = json.loads((ROOT / "apps/publishers.json").read_text())
    pin = next((pin for pin in pins if pin["key_id"] == key_id and pin["public_key"] == public), None)
    versions = json.loads((ROOT / "apps/versions.json").read_text())
    if pin is None or not {app["id"] for app in versions["apps"].values()} <= set(pin["app_ids"]):
        raise ValueError("publisher must match the shipped pin for the root and every cell")
    prepared = {}
    node_apps = versions.get("node_apps", {})
    if (node_apps or ledger_path is not None) and "inbe." not in pin.get("app_prefixes", []):
        raise ValueError("publisher pin must cover the apps the node offers")
    if suspend and only is None:
        raise ValueError("--suspend needs the one --app to suspend")
    for name, component in ledger_components(versions, ledger_path, only):
        try:
            request = Request(origin.rstrip("/") + "/api/v1/apps/" + component["id"],
                              headers={"User-Agent": "Inbe-Publisher/1.0", "Accept": "application/json"})
            with open_url(request, timeout=30) as response:
                data = response.read(65537)
            if len(data) > 65536:
                raise ValueError("registry response exceeds its size limit")
            existing = json.loads(data)
        except HTTPError as error:
            if error.code != 404:
                raise
            existing = {}
        if suspend:
            manifest = suspension_for(component["id"], existing, key_id, public, manifest_sequence)
        else:
            manifest = manifest_for(dict(component, name=name), existing, key_id, public)
        prepared[component["id"]] = signed_registration(manifest, publisher, authority)
    output.mkdir(parents=True, exist_ok=True)
    (output / "registry-public-key.hex").write_text(public_hex(authority) + "\n")
    for app_id, request in prepared.items():
        (output / (app_id + ".json")).write_text(json.dumps(request, ensure_ascii=False) + "\n")
    return prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--publisher-key", required=True, type=Path)
    parser.add_argument("--approval-key", required=True, type=Path)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--app-ledger", type=Path, help="owning project's node-app version ledger")
    parser.add_argument("--app", help="prepare only this app, such as arcade")
    parser.add_argument("--suspend", action="store_true",
                        help="prepare the --app's suspension instead of its registration")
    parser.add_argument("--manifest-sequence", type=int, default=0,
                        help="manifest sequence above the node's, required with --suspend")
    args = parser.parse_args()
    try:
        requests = registrations(args.origin, args.publisher_key, args.approval_key, args.key_id, args.output,
                                 ledger_path=args.app_ledger, only=args.app, suspend=args.suspend,
                                 manifest_sequence=args.manifest_sequence)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    if args.suspend:
        print(f"Prepared the signed suspension of {next(iter(requests))}; its keys and scopes are unchanged")
        return
    print(f"Prepared {len(requests)} signed registrations; existing scopes and keys retained")


if __name__ == "__main__":
    main()
