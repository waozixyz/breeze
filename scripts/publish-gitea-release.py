#!/usr/bin/env python3
"""Publish and read back the exact downloads produced by the Release workflow.

The workflow must have pushed its tag first. This command never creates tags
or replaces attachments. A rerun inspects and verifies existing attachments
before continuing an interrupted draft. GITEA_TOKEN is read from stdin when
--token-stdin is supplied; the token is never placed in command arguments.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = "https://git.waozi.xyz"
REPOSITORY = "waozi/breeze"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Gitea:
    def __init__(self, origin, token):
        self.origin = origin.rstrip("/")
        self.headers = {"Authorization": "token " + token, "Host": "git.waozi.xyz",
                        "User-Agent": "Breeze-Release/1.0"}

    def api(self, path, *, method="GET", body=None, missing=False, data=None, headers=None):
        request_headers = {**self.headers, "Accept": "application/json", **(headers or {})}
        if body is not None:
            data = json.dumps(body).encode()
            request_headers["Content-Type"] = "application/json"
        request = Request(f"{self.origin}/api/v1/repos/{REPOSITORY}/{path}", data=data,
                          headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=600) as response:
                return json.load(response)
        except HTTPError as error:
            if missing and error.code == 404:
                return None
            raise RuntimeError(f"Gitea {method} {path}: HTTP {error.code}") from None

    def verify(self, asset, path, expected, tag):
        if asset["name"] != path.name or asset["size"] != path.stat().st_size:
            raise ValueError(f"Attachment metadata differs: {path.name}")
        url = urlsplit(asset["browser_download_url"])
        attachment = "/attachments/" + str(uuid.UUID(asset["uuid"]))
        release_path = f"/{REPOSITORY}/releases/download/{tag}/" + quote(path.name)
        if url.scheme not in ("http", "https") or url.netloc != "git.waozi.xyz" or \
                url.path not in (attachment, release_path) or url.query or url.fragment:
            raise ValueError(f"Unexpected attachment URL: {path.name}")
        request = Request(self.origin + attachment, headers=self.headers)
        with urlopen(request, timeout=600) as response:
            actual = hashlib.file_digest(response, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Downloaded attachment differs: {path.name}")

    def upload(self, release_id, path):
        boundary = "breeze-" + uuid.uuid4().hex
        prefix = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"attachment\"; "
                  f"filename=\"{path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        suffix = f"\r\n--{boundary}--\r\n".encode()

        def chunks():
            yield prefix
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    yield chunk
            yield suffix

        return self.api(f"releases/{release_id}/assets?" + urlencode({"name": path.name}),
                        method="POST", data=chunks(), headers={
                            "Content-Type": "multipart/form-data; boundary=" + boundary,
                            "Content-Length": str(len(prefix) + path.stat().st_size + len(suffix))})


def publish(client, version, revision, directory, notes):
    tag = "v" + version
    tagged = client.api("tags/" + quote(tag, safe=""))
    if tagged["commit"]["sha"] != revision:
        raise ValueError("The workflow's Gitea tag does not select the verified candidate")
    expected = subprocess.check_output(["sh", ROOT / "scripts/list-expected-release-assets.sh",
                                        version], text=True).splitlines()
    expected.append("appcast.json")
    for name in expected:
        path = directory / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError("Missing release artifact: " + name)
    assets = sorted(path for path in directory.iterdir() if path.is_file())
    if any(path.is_symlink() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", path.name)
           for path in assets):
        raise ValueError("Unexpected release artifact path")
    hashes = {path.name: digest(path) for path in assets}
    marker = f"<!-- breeze-source:{revision} -->"
    body = notes.strip() + "\n\n" + marker
    release = client.api("releases/tags/" + quote(tag, safe=""), missing=True)
    if release is None:
        release = client.api("releases", method="POST", body={
            "tag_name": tag, "target_commitish": revision, "name": "Inner Breeze " + version,
            "body": body, "draft": True, "prerelease": False})
    if release["tag_name"] != tag or release["prerelease"] or marker not in release["body"]:
        raise ValueError("The existing release belongs to different content")
    release_id = release["id"]
    attached = client.api(f"releases/{release_id}/assets")
    by_name = {}
    for asset in attached:
        if asset["name"] in by_name or asset["name"] not in hashes:
            raise ValueError("Unexpected or duplicate release attachment")
        by_name[asset["name"]] = asset
    if not release["draft"] and set(by_name) != set(hashes):
        raise ValueError("A published release is incomplete; it was left unchanged")
    for path in assets:
        asset = by_name.get(path.name)
        if asset is None:
            asset = client.upload(release_id, path)
        client.verify(asset, path, hashes[path.name], tag)
        by_name[path.name] = asset
        print(f"Verified {path.name}: {hashes[path.name]}", flush=True)
    # Inspect again after uploads before exposing the release to users.
    attached = client.api(f"releases/{release_id}/assets")
    identity = lambda asset: (asset["name"], asset["id"], asset["uuid"], asset["size"])
    if len(attached) != len(assets) or \
            {identity(asset) for asset in attached} != {identity(asset) for asset in by_name.values()}:
        raise ValueError("Release attachments changed during verification")
    if client.api("tags/" + quote(tag, safe=""))["commit"]["sha"] != revision:
        raise ValueError("Release tag changed during verification")
    if release["draft"]:
        release = client.api(f"releases/{release_id}", method="PATCH", body={"draft": False})
    release = client.api(f"releases/{release_id}")
    if release["draft"] or release["tag_name"] != tag:
        raise ValueError("Gitea did not publish the verified release")
    print(f"Published {PUBLIC}/{REPOSITORY}/releases/tag/{tag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--assets", type=Path, default=ROOT / "build/release")
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--origin", default=PUBLIC,
                        help="Gitea origin, or its loopback address through an administrative SSH forward")
    parser.add_argument("--token-stdin", action="store_true")
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if args.origin != PUBLIC and not (origin.scheme == "http" and origin.hostname == "127.0.0.1"
                                      and origin.port and not origin.path and not origin.query
                                      and not origin.fragment and not origin.username):
        parser.error("use the public Gitea origin or an HTTP loopback forward")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version) or \
            not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("a numeric version and full verified commit are required")
    token = sys.stdin.readline().strip() if args.token_stdin else os.environ.get("GITEA_TOKEN", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        parser.error("GITEA_TOKEN or --token-stdin is required")
    publish(Gitea(args.origin, token), args.version, args.revision,
            args.assets, args.notes.read_text())


if __name__ == "__main__":
    main()
