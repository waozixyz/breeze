#!/usr/bin/env python3
import base64
import argparse
import importlib.util
import hashlib
import json
import mimetypes
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"
UPLOAD_BASE = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3"


def load_env_file(path):
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env: {name}")
    return value


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign_rs256(message, private_key):
    key_file = tempfile.NamedTemporaryFile("w", delete=False)
    try:
        key_file.write(private_key)
        key_file.close()
        os.chmod(key_file.name, 0o600)
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_file.name],
            input=message.encode("ascii"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return result.stdout
    finally:
        try:
            os.unlink(key_file.name)
        except OSError:
            pass


def service_account_token(json_path):
    account = json.loads(pathlib.Path(json_path).read_text())
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": account["client_email"],
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    )
    signature = b64url(sign_rs256(signing_input, account["private_key"]))
    assertion = signing_input + "." + signature
    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode("utf-8")
    data = http_request(
        "POST",
        TOKEN_URL,
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        token=None,
    )
    return json.loads(data.decode("utf-8"))["access_token"]


def http_request(method, url, body=None, headers=None, token=None):
    request = urllib.request.Request(url, data=body, method=method)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} failed: HTTP {exc.code}\n{detail}") from exc


def api_url(package_name, path):
    package = urllib.parse.quote(package_name, safe="")
    return f"{API_BASE}/applications/{package}{path}"


def upload_url(package_name, path):
    package = urllib.parse.quote(package_name, safe="")
    return f"{UPLOAD_BASE}/applications/{package}{path}"


def list_images(images_root, image_type):
    folder = images_root / image_type
    if not folder.is_dir():
        print(f"Skipping missing folder: {folder}")
        return []
    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not files:
        print(f"Skipping empty folder: {folder}")
    return files


def listing_texts(metadata_root):
    """Short and full descriptions for each Fastlane locale folder."""
    texts = {}
    for folder in sorted(metadata_root.iterdir()):
        short = folder / "short_description.txt"
        full = folder / "full_description.txt"
        if folder.is_dir() and short.is_file() and full.is_file():
            texts[folder.name] = {
                "shortDescription": short.read_text().strip(),
                "fullDescription": full.read_text().strip(),
            }
    return texts


def upload_listing_texts(package_name, edit_id, metadata_root, token):
    existing = json.loads(http_request(
        "GET", api_url(package_name, f"/edits/{edit_id}/listings"), token=token))
    listings = {item["language"]: item for item in existing.get("listings", [])}
    title = listings.get("en-US", {}).get("title", "Inner Breeze")
    for language, text in listing_texts(metadata_root).items():
        if len(text["shortDescription"]) > 80 or len(text["fullDescription"]) > 4000:
            raise SystemExit(f"{language} description is over Play's length limit")
        path = api_url(package_name, f"/edits/{edit_id}/listings/{language}")
        body = dict(text)
        # Titles stay as they are on Play; a new translation borrows en-US's.
        method = "PATCH" if language in listings else "PUT"
        if method == "PUT":
            body["language"] = language
            body["title"] = title
        http_request(
            method,
            path,
            body=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            token=token,
        )
        print(f"Updated {language} listing text")


def main():
    parser = argparse.ArgumentParser(description="Preflight, validate, or publish reviewed Play listing assets.")
    parser.add_argument("--preflight-only", action="store_true", help="Check local assets without credentials or network access")
    args = parser.parse_args()
    load_env_file(ROOT / ".env.play")
    language = os.environ.get("PLAY_LANGUAGE", "en-US")
    images_root = pathlib.Path(
        os.environ.get(
            "PLAY_METADATA_IMAGES_DIR",
            str(ROOT / "fastlane/metadata/android/en-US/images"),
        )
    )
    image_types = [
        item.strip()
        for item in os.environ.get(
            "PLAY_IMAGE_TYPES",
            "phoneScreenshots,sevenInchScreenshots,tenInchScreenshots",
        ).split(",")
        if item.strip()
    ]
    metadata_root = pathlib.Path(
        os.environ.get("PLAY_METADATA_DIR", str(ROOT / "fastlane/metadata/android")))
    listing_text = os.environ.get("PLAY_LISTING_TEXT", "1") != "0"
    commit = os.environ.get("PLAY_COMMIT", "0") == "1"
    delete_existing = os.environ.get("PLAY_DELETE_EXISTING", "1") != "0"

    spec = importlib.util.spec_from_file_location("screenshot_harness", ROOT / "scripts/screenshot-harness.py")
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    harness.store_preflight(images_root)
    if listing_text:
        for locale, text in listing_texts(metadata_root).items():
            if len(text["shortDescription"]) > 80 or len(text["fullDescription"]) > 4000:
                raise SystemExit(f"{locale} description is over Play's length limit")
    allowed_types = {"phoneScreenshots", "sevenInchScreenshots", "tenInchScreenshots"}
    if not image_types or not set(image_types) <= allowed_types:
        raise SystemExit("PLAY_IMAGE_TYPES must name reviewed phone/tablet screenshot types")
    if args.preflight_only:
        print("Local listing preflight passed; no Google Play edit was created.")
        return

    reviewed_hashes = {item["file"]: item["sha256"] for item in
                       json.loads((images_root / "screenshot-review.json").read_text())["files"]}
    image_payloads = {}
    for image_type in image_types:
        image_payloads[image_type] = []
        for path in list_images(images_root, image_type):
            data = path.read_bytes()
            relative = str(path.relative_to(images_root))
            if hashlib.sha256(data).hexdigest() != reviewed_hashes.get(relative):
                raise SystemExit(f"Store image changed after preflight: {path}")
            image_payloads[image_type].append((path, data))

    package_name = required_env("PLAY_PACKAGE_NAME")
    service_account = required_env("PLAY_SERVICE_ACCOUNT_JSON")

    token = service_account_token(service_account)
    edit = json.loads(http_request("POST", api_url(package_name, "/edits"), token=token))
    edit_id = edit["id"]
    print(f"Created Google Play edit: {edit_id}")

    try:
        if listing_text:
            upload_listing_texts(package_name, edit_id, metadata_root, token)
        for image_type in image_types:
            files = image_payloads[image_type]
            if not files:
                continue
            listing_path = f"/edits/{edit_id}/listings/{language}/{image_type}"
            if delete_existing:
                http_request("DELETE", api_url(package_name, listing_path), token=token)
                print(f"Cleared {language}/{image_type}")
            for path, data in files:
                mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
                url = upload_url(package_name, listing_path) + "?uploadType=media"
                http_request(
                    "POST",
                    url,
                    body=data,
                    headers={"Content-Type": mime},
                    token=token,
                )
                print(f"Uploaded {image_type}/{path.name}")

        harness.store_preflight(images_root)
        http_request("POST", api_url(package_name, f"/edits/{edit_id}:validate"), token=token)
        if commit:
            http_request("POST", api_url(package_name, f"/edits/{edit_id}:commit"), token=token)
            print("Committed the store listing to Google Play.")
        else:
            http_request("DELETE", api_url(package_name, f"/edits/{edit_id}"), token=token)
            print("Validated the store listing and deleted the draft edit. Set PLAY_COMMIT=1 to publish.")
    except BaseException:
        try:
            http_request("DELETE", api_url(package_name, f"/edits/{edit_id}"), token=token)
            print(f"Deleted failed edit: {edit_id}", file=sys.stderr)
        except BaseException:
            pass
        raise


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(f"Play preflight blocked: {error}") from None
