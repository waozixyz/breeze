#!/usr/bin/env python3
"""Build and publish Inbe's independently signed Daochi release v2 files."""
import argparse
from contextlib import ExitStack
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROOT = Path(__file__).resolve().parent.parent
NAMES = ("habits", "practices", "lumi", "lists", "diary", "inbe")
IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9_.-]{0,62}\Z")
VERSION = re.compile(r"(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\Z")


def signing_message(value):
    fields = ("app_id", "sequence", "version", "runtime", "host_api",
              "module_api", "data_schema", "key_id")
    lines = ["daochi-zib-release-v2", *(str(value[name]) for name in fields),
             str(len(value["artifacts"]))]
    for artifact in value["artifacts"]:
        lines.extend(str(artifact[name]) for name in ("variant", "sha256", "size"))
    lines.append(str(len(value["dependencies"])))
    for dependency in value["dependencies"]:
        lines.extend(str(dependency[name]) for name in ("app_id", "version", "sha256", "size"))
    return ("\n".join(lines) + "\n").encode("ascii")


def atomic_write(path, data):
    fd, name = tempfile.mkstemp(prefix=".inbe-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(name).unlink(missing_ok=True)


def stage(store, key_path, key_id, publishers_path=None):
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
        path = ROOT / "build" / ("inbe.zib" if name == "inbe" else f"cells/{name}.zib")
        data = path.read_bytes()
        if not data.startswith(b"ZIB\0") or not 8 <= len(data) <= 64 * 1024 * 1024:
            raise ValueError(f"invalid {name} bundle")
        artifact = dict(variant="module", sha256=sha256(data).hexdigest(), size=len(data))
        dependencies = []
        if name == "inbe":
            for child in ("habits", "practices", "lumi", "lists", "diary"):
                release = releases[child]
                nested = payloads[child]
                if data.count(nested) != 1:
                    raise ValueError(f"root does not contain the exact {child} release")
                dependencies.append(dict(app_id=release["app_id"], version=release["version"],
                                         sha256=release["artifacts"][0]["sha256"], size=len(nested)))
        value = dict(app_id=component["id"], sequence=sequence, version=component["version"],
                     runtime="kryon-app-v1", host_api=versions["host_api"],
                     module_api=versions["module_api"], data_schema=0, key_id=key_id,
                     artifacts=[artifact], dependencies=sorted(dependencies, key=lambda d: d["app_id"]))
        value["signature"] = key.sign(signing_message(value)).hex()
        releases[name] = value
        payloads[name] = data
    store.mkdir(parents=True, exist_ok=True)
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
            payload = directory / (value["artifacts"][0]["sha256"] + ".zib")
            archive = directory / f"release-{value['sequence']}.json"
            if payload.exists() and payload.read_bytes() != payloads[name]:
                raise ValueError("immutable payload does not match its hash")
            if archive.exists() and archive.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
        for name in NAMES:
            value = releases[name]
            directory = store / value["app_id"]
            encoded = (json.dumps(value, separators=(",", ":")) + "\n").encode()
            if len(encoded) > 65536:
                raise ValueError("release metadata exceeds the client limit")
            payload = directory / (value["artifacts"][0]["sha256"] + ".zib")
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


def publish(store, target, remote_store):
    if not re.fullmatch(r"[a-zA-Z0-9_.@-]+", target) or target.startswith("-"):
        raise ValueError("invalid SSH target")
    if not remote_store.startswith("/") or "\n" in remote_store:
        raise ValueError("Daochi package store must be an absolute path")
    # The node installs the importer independently. The upload key may be
    # restricted to this one command and this fixed store; it needs no shell,
    # SFTP access or permission to change the server's code and configuration.
    with tempfile.TemporaryDirectory(prefix="inbe-upload-") as staging:
        import tarfile
        archive = Path(staging) / "packages.tar"
        with tarfile.open(archive, "w") as tar:
            for name in NAMES:
                app_id = "inbe" if name == "inbe" else "inbe." + name
                directory = store / app_id
                value = json.loads((directory / "latest-v2.json").read_bytes())
                payload = value["artifacts"][0]["sha256"] + ".zib"
                for filename in ("latest-v2.json", payload, payload + ".release-v2.json",
                                 f"release-{value['sequence']}.json"):
                    path = directory / filename
                    tar.add(path, arcname=str(path.relative_to(store)), recursive=False)
        options = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes"]
        if os.environ.get("INBE_SSH_IDENTITY"):
            options += ["-i", os.environ["INBE_SSH_IDENTITY"]]
        if os.environ.get("INBE_SSH_KNOWN_HOSTS"):
            options += ["-o", "UserKnownHostsFile=" + os.environ["INBE_SSH_KNOWN_HOSTS"]]
        command = shlex.join(["inbe-packages", remote_store])
        with archive.open("rb") as upload:
            subprocess.run(["ssh", *options, "--", target, command], stdin=upload, check=True)


def open_public_url(url, timeout):
    return urlopen(Request(url, headers={"User-Agent": "Inbe-Publisher/1.0"}), timeout=timeout)


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
        with open_url(route + "/latest", timeout=30) as response:
            encoded = response.read(65537)
        if len(encoded) > 65536 or json.loads(encoded) != expected:
            raise ValueError(f"{app_id}: public release metadata differs from the signed publication")
        artifact = expected["artifacts"][0]
        digest = artifact["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not 8 <= artifact["size"] <= 64 * 1024 * 1024:
            raise ValueError(f"{app_id}: invalid staged artifact")
        checksum = sha256()
        size = 0
        with open_url(route + "/" + digest + ".zib", timeout=30) as response:
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
    print("Verified public signed metadata and package bytes for the root and all five cells")


def validate_release(value, app_id, publishers):
    fields = {"app_id", "sequence", "version", "runtime", "host_api", "module_api",
              "data_schema", "key_id", "artifacts", "dependencies", "signature"}
    if not isinstance(value, dict) or set(value) != fields or value["app_id"] != app_id or \
            value["runtime"] != "kryon-app-v1":
        raise ValueError("invalid release identity or fields")
    if not isinstance(value["version"], str) or not VERSION.fullmatch(value["version"]):
        raise ValueError("invalid numeric release version")
    for field, minimum, maximum in (("sequence", 1, 2**31 - 1), ("host_api", 1, 65535),
                                     ("module_api", 1, 65535), ("data_schema", 0, 65535)):
        if type(value[field]) is not int or not minimum <= value[field] <= maximum:
            raise ValueError("invalid release sequence or API version")
    if not isinstance(value["artifacts"], list) or len(value["artifacts"]) != 1:
        raise ValueError("Inbe release must contain exactly one module artifact")
    artifact = value["artifacts"][0]
    if not isinstance(artifact, dict) or set(artifact) != {"variant", "sha256", "size"} or \
            artifact["variant"] != "module" or not isinstance(artifact["sha256"], str) or \
            not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) or \
            type(artifact["size"]) is not int or not 8 <= artifact["size"] <= 64 * 1024 * 1024:
        raise ValueError("invalid module artifact")
    dependencies = value["dependencies"]
    expected = sorted("inbe." + name for name in NAMES if name != "inbe") if app_id == "inbe" else []
    if not isinstance(dependencies, list) or len(dependencies) != len(expected):
        raise ValueError("invalid root dependencies")
    for dependency, expected_id in zip(dependencies, expected):
        if not isinstance(dependency, dict) or set(dependency) != {"app_id", "version", "sha256", "size"} or \
                dependency["app_id"] != expected_id or not isinstance(dependency["version"], str) or \
                not VERSION.fullmatch(dependency["version"]) or not isinstance(dependency["sha256"], str) or \
                not re.fullmatch(r"[0-9a-f]{64}", dependency["sha256"]) or \
                type(dependency["size"]) is not int or not 8 <= dependency["size"] <= 64 * 1024 * 1024:
            raise ValueError("invalid dependency descriptor")
    pin = next((pin for pin in publishers if pin["key_id"] == value["key_id"] and
                app_id in pin["app_ids"]), None)
    if pin is None:
        raise ValueError("publisher is not trusted for this app")
    try:
        if not isinstance(value["signature"], str) or not re.fullmatch(r"[0-9a-f]{128}", value["signature"]):
            raise ValueError("invalid release signature")
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pin["public_key"])).verify(
            bytes.fromhex(value["signature"]), signing_message(value))
    except Exception as error:
        raise ValueError("release signature rejected") from error


def import_archive(archive, store, publishers_path=None):
    """Node-side merge. Daochi still checks registry/key status on every GET."""
    import tarfile
    publishers = json.loads((publishers_path or ROOT / "apps/publishers.json").read_text())
    ids = {"inbe", "inbe.habits", "inbe.practices", "inbe.lists", "inbe.diary", "inbe.lumi"}
    entries = {}
    total = 0
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if len(parts) != 2 or parts[0] not in ids or not member.isfile() or member.size > 64 * 1024 * 1024:
                raise ValueError("invalid archive member")
            if member.name in entries:
                raise ValueError("duplicate archive member")
            total += member.size
            if len(entries) >= 24 or total > 6 * 64 * 1024 * 1024 + 1024 * 1024:
                raise ValueError("archive exceeds the release size limit")
            entries[member.name] = tar.extractfile(member).read()
    with ExitStack() as stack:
        releases = {}
        for app_id in sorted(ids):
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
            data = entries[f"{app_id}/{artifact['sha256']}.zib"]
            if artifact["size"] != len(data) or sha256(data).hexdigest() != artifact["sha256"]:
                raise ValueError("payload hash mismatch")
            if not data.startswith(b"ZIB\0"):
                raise ValueError("payload is not a ZIB bundle")
            current = directory / "latest-v2.json"
            if current.exists():
                old = json.loads(current.read_bytes())
                if old != value and (old["sequence"] >= value["sequence"] or
                        tuple(map(int, old["version"].split("."))) >=
                        tuple(map(int, value["version"].split(".")))):
                    raise ValueError("release must advance the installed version and sequence")
            archived = directory / f"release-{value['sequence']}.json"
            if archived.exists() and archived.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
            releases[app_id] = (value, encoded, data)
        root = releases["inbe"]
        for dependency in root[0]["dependencies"]:
            child, _, payload = releases[dependency["app_id"]]
            artifact = child["artifacts"][0]
            if dependency != dict(app_id=child["app_id"], version=child["version"],
                                  sha256=artifact["sha256"], size=artifact["size"]) or root[2].count(payload) != 1:
                raise ValueError("root does not contain its exact signed cell dependency")
        # Dependencies go first. Publishing the root is the final step.
        for app_id in sorted(ids, key=lambda value: value == "inbe"):
            value, encoded, data = releases[app_id]
            directory = store / app_id
            payload = directory / (value["artifacts"][0]["sha256"] + ".zib")
            archived = directory / f"release-{value['sequence']}.json"
            if archived.exists() and archived.read_bytes() != encoded:
                raise ValueError("release sequence is already occupied")
            atomic_write(payload, data)
            atomic_write(payload.with_name(payload.name + ".release-v2.json"), encoded)
            atomic_write(archived, encoded)
            atomic_write(directory / "latest-v2.json", encoded)
    archive.unlink()
    archive.parent.rmdir()


def receive_archive(store, publishers_path):
    if shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND", "")) != ["inbe-packages", str(store)]:
        raise ValueError("upload key permits only publication to its configured package store")
    with tempfile.TemporaryDirectory(prefix="inbe-receive-") as directory:
        archive = Path(directory) / "packages.tar"
        maximum = 5 * 64 * 1024 * 1024 + 1024 * 1024
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
    args = parser.parse_args()
    try:
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
                publish(args.store, args.ssh_target, args.remote_store)
            if args.verify_origin:
                verify_origin(args.store, args.verify_origin)
        print("Inbe package releases published" if args.ssh_target or args.import_archive or args.receive_archive else "Inbe package releases staged")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Package publication failed: {error}\n")


if __name__ == "__main__":
    main()
