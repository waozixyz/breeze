#!/usr/bin/env python3
"""Generate independent signature vectors and execute the shipped Zi verifier."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tarfile
from io import BytesIO

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("inbe_release", ROOT / "scripts/package-release.py")
release_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_tool)


def main():
    work = ROOT / "build/package-release-test"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="inbe-release-test-") as directory:
        fixtures = Path(directory)
        key = Ed25519PrivateKey.generate()
        private = fixtures / "key.pem"
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                            serialization.PrivateFormat.PKCS8,
                                            serialization.NoEncryption()))
        private.chmod(0o600)
        public = key.public_key().public_bytes(serialization.Encoding.Raw,
                                              serialization.PublicFormat.Raw).hex()
        ids = ["inbe", "inbe.lists", "inbe.habits", "inbe.practices", "inbe.diary", "inbe.lumi",
               "inbe.leaderboard"]
        publishers = fixtures / "publishers.json"
        publishers.write_text(json.dumps([dict(key_id="test-key", public_key=public, app_ids=ids)]))
        store = fixtures / "store"
        values = release_tool.stage(store, private, "test-key", publishers)
        release_tool.stage(store, private, "test-key", publishers)  # idempotent

        def served(url, timeout):
            assert timeout == 30
            prefix = "https://node.example/api/v2/packages/"
            assert url.startswith(prefix)
            app_id, filename = url.removeprefix(prefix).split("/")
            # The publisher asks as bucket 0, which receives staged releases first.
            if filename.startswith("latest"):
                assert filename == "latest?bucket=0", filename
                filename = "latest-v2.json"
            return BytesIO((store / app_id / filename).read_bytes())

        release_tool.verify_origin(store, "https://node.example", served)
        for failure in ("metadata", "hash", "truncated", "oversized"):
            def damaged(url, timeout):
                content = served(url, timeout).read()
                if failure == "metadata" and "/latest" in url:
                    return BytesIO(b"{}")
                if url.endswith(".zib"):
                    if failure == "hash":
                        content = content[:-1] + bytes([content[-1] ^ 1])
                    elif failure == "truncated":
                        content = content[:-1]
                    elif failure == "oversized":
                        content += b"extra"
                return BytesIO(content)
            try:
                release_tool.verify_origin(store, "https://node.example", damaged)
            except ValueError:
                pass
            else:
                raise AssertionError(f"public {failure} was accepted")
        remote = fixtures / "remote-store"
        for attempt in range(2):
            staging = fixtures / f"upload-{attempt}"
            staging.mkdir()
            archive = staging / "packages.tar"
            with tarfile.open(archive, "w") as tar:
                for path in sorted(store.rglob("*")):
                    if path.is_file() and path.name != ".publish.lock":
                        tar.add(path, arcname=str(path.relative_to(store)))
            release_tool.import_archive(archive, remote, publishers)
            assert not staging.exists()
            for value in values.values():
                assert json.loads((remote / value["app_id"] / "latest-v2.json").read_bytes()) == value
        # A staged upload holds changed releases back until it is promoted or
        # expires; unchanged re-uploads keep the staging.
        def upload(name, rollout_text):
            staging = fixtures / name
            staging.mkdir()
            archive = staging / "packages.tar"
            with tarfile.open(archive, "w") as tar:
                for path in sorted(store.rglob("*")):
                    if path.is_file() and path.name != ".publish.lock":
                        tar.add(path, arcname=str(path.relative_to(store)))
                if rollout_text is not None:
                    data = rollout_text.encode()
                    member = tarfile.TarInfo("rollout.json")
                    member.size = len(data)
                    tar.addfile(member, BytesIO(data))
            return archive

        staged_remote = fixtures / "staged-remote"
        release_tool.import_archive(upload("staged-0", '{"percent": 20, "hours": 24}'), staged_remote, publishers)
        for value in values.values():
            staged = json.loads((staged_remote / value["app_id"] / "rollout.json").read_text())
            assert staged["sequence"] == value["sequence"] and staged["percent"] == 20, staged
            assert 0 < staged["until"] - time.time() <= 24 * 3600, staged
        release_tool.import_archive(upload("staged-1", None), staged_remote, publishers)
        assert (staged_remote / "inbe.diary" / "rollout.json").exists()
        release_tool.import_archive(upload("staged-2", '{"percent": 100, "hours": 1}'), staged_remote, publishers)
        assert not list(staged_remote.rglob("rollout.json"))
        for index, bad in enumerate(('{"percent": 0, "hours": 24}', '{"percent": 20, "hours": 0}',
                                     '{"percent": 20, "hours": 24, "extra": 1}', '[]', '{')):
            try:
                release_tool.import_archive(upload(f"staged-bad-{index}", bad), staged_remote, publishers)
            except ValueError:
                pass
            else:
                raise AssertionError(f"invalid rollout {bad} was accepted")
        # A node updated for Leaderboard still imports archives staged before it.
        names = release_tool.NAMES
        release_tool.NAMES = tuple(name for name in names if name != "leaderboard")
        try:
            older = fixtures / "older-store"
            release_tool.stage(older, private, "test-key", publishers)
            staging = fixtures / "older-upload"
            staging.mkdir()
            archive = staging / "packages.tar"
            with tarfile.open(archive, "w") as tar:
                for path in sorted(older.rglob("*")):
                    if path.is_file() and path.name != ".publish.lock":
                        tar.add(path, arcname=str(path.relative_to(older)))
            release_tool.import_archive(archive, fixtures / "older-remote", publishers)
            assert not (fixtures / "older-remote" / "inbe.leaderboard").exists()
        finally:
            release_tool.NAMES = names
        staging = fixtures / "invalid-upload"
        staging.mkdir()
        archive = staging / "packages.tar"
        with tarfile.open(archive, "w") as tar:
            tar.add(publishers, arcname="../publishers.json")
        try:
            release_tool.import_archive(archive, remote, publishers)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe archive path was accepted")
        # Compare against the node's canonical format when its source is here.
        node = ROOT.parent.parent / "kryonlabs/daochi/scripts/app_release.py"
        if node.exists():
            spec = importlib.util.spec_from_file_location("node_release", node)
            protocol = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(protocol)
            for value in values.values():
                assert protocol.signing_message(value) == release_tool.signing_message(value)
        (fixtures / "public").write_text(public)
        names = ("inbe", "lists", "habits", "practices", "diary", "lumi")
        for name in names:
            (fixtures / name).write_text(json.dumps(values[name]))

        def altered(name, change, resign=True):
            value = json.loads(json.dumps(values["habits"]))
            change(value)
            if resign:
                value["signature"] = key.sign(release_tool.signing_message(value)).hex()
            (fixtures / name).write_text(json.dumps(value))

        altered("wrong-app", lambda value: value.update(app_id="inbe.diary"))
        # The host runs releases built for any interface it still supports.
        ledger = json.loads((ROOT / "apps/versions.json").read_text())
        altered("wrong-api", lambda value: value.update(host_api=ledger["host_api"] + 1))
        altered("old-api", lambda value: value.update(host_api=ledger["oldest_host_api"] - 1))
        altered("oldest-api", lambda value: value.update(host_api=ledger["oldest_host_api"]))
        altered("current-api", lambda value: value.update(host_api=ledger["host_api"]))
        altered("wrong-module", lambda value: value.update(module_api=ledger["module_api"] + 1))
        altered("bad-signature", lambda value: value.update(version="9.0.0"), False)
        altered("fraction", lambda value: value.update(sequence=1.5))
        altered("negative", lambda value: value.update(sequence=-1))
        altered("runtime", lambda value: value.update(runtime="other"))
        altered("bad-version", lambda value: value.update(version="01.0.0"))
        altered("extra-dependency", lambda value: value.update(dependencies=values["inbe"]["dependencies"]))
        root = json.loads(json.dumps(values["inbe"]))
        root["dependencies"][0]["sha256"] = "0" * 64
        root["signature"] = key.sign(release_tool.signing_message(root)).hex()
        (fixtures / "wrong-nested").write_text(json.dumps(root))
        root_data = (ROOT / "build/inbe.zib").read_bytes()
        (fixtures / "root-bytes").write_bytes(root_data)
        updated_root = json.loads(json.dumps(values["inbe"]))
        root_version = list(map(int, values["inbe"]["version"].split(".")))
        root_version[2] += 1
        updated_root.update(sequence=values["inbe"]["sequence"] + 1,
                            version=".".join(map(str, root_version)))
        for dependency in updated_root["dependencies"]:
            if dependency["app_id"] == "inbe.habits":
                dependency["version"] = "1.1.0"
            elif dependency["app_id"] == "inbe.practices":
                dependency["version"] = "1.2.0"
        updated_root["signature"] = key.sign(release_tool.signing_message(updated_root)).hex()
        (fixtures / "root-new").write_text(json.dumps(updated_root))
        data = (ROOT / "build/cells/habits.zib").read_bytes()
        (fixtures / "habits-bytes").write_bytes(data)
        (fixtures / "corrupt-bytes").write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        (fixtures / "diary-bytes").write_bytes((ROOT / "build/cells/diary.zib").read_bytes())
        updated = json.loads(json.dumps(values["diary"]))
        diary_version = list(map(int, updated["version"].split(".")))
        diary_version[2] += 1
        updated.update(sequence=updated["sequence"] + 1, version=".".join(map(str, diary_version)))
        updated["signature"] = key.sign(release_tool.signing_message(updated)).hex()
        (fixtures / "diary-new").write_text(json.dumps(updated))
        diary_version[2] += 1
        updated["version"] = ".".join(map(str, diary_version))
        (fixtures / "diary-bad").write_text(json.dumps(updated))
        ziran = ROOT / "build/ziran-toolchain/bin/ziran"
        subprocess.run([str(ziran), "build", "--target=c", "--no-main", "--root", str(ROOT / "tests"),
                        "--module-path", str(ROOT / "src"), "--module-path", str(ROOT / "build/packages/ziran/std"),
                        "--module-path", str(ROOT / "build/packages/kryon/src/ui"),
                        "--module-path", str(ROOT / "build/packages/daochi-client"),
                        "-o", str(work / "generated"), str(ROOT / "tests/package_release_behavior.zi")], check=True)
        sources = list((work / "generated").rglob("*.c"))
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-D_GNU_SOURCE", "-O1",
                        "-ffunction-sections", "-fdata-sections", "-I" + str(work / "generated"),
                        "-I" + str(ROOT / "build/packages/ziran/include"),
                        "-I" + str(ROOT / "build/packages/monocypher/src"),
                        "-I" + str(ROOT / "build/packages/monocypher/src/optional"),
                        str(ROOT / "tests/package_release_host.c"), *(str(path) for path in sources),
                        str(ROOT / "build/packages/monocypher/src/monocypher.c"),
                        str(ROOT / "build/packages/monocypher/src/optional/monocypher-ed25519.c"),
                        str(ROOT / "build/ziran-toolchain/libziran.a"), "-Wl,--gc-sections", "-lm",
                        "-o", str(work / "test")], check=True)
        subprocess.run([str(work / "test"), str(fixtures)], check=True)
        generated = work / "manager"
        subprocess.run([str(ziran), "build", "--target=c", "--no-main", "--root", str(ROOT / "tests"),
                        "--module-path", str(ROOT / "src"), "--module-path", str(ROOT / "build/packages/ziran/std"),
                        "--module-path", str(ROOT / "build/packages/kryon/src/ui"),
                        "--module-path", str(ROOT / "build/packages/kryon/src/backend"),
                        "--module-path", str(ROOT / "build/packages/daochi-client"),
                        "--module-path", str(ROOT / "build/packages/kss/src"),
                        "--module-path", str(ROOT / "build/packages/game2d/src"),
                        "--module-path", "oqs=" + str(ROOT / "build/packages/oqs/src"),
                        "-o", str(generated), str(ROOT / "tests/package_manager_behavior.zi")], check=True)
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-D_GNU_SOURCE", "-O1",
                        "-ffunction-sections", "-fdata-sections", "-I" + str(generated),
                        "-I" + str(ROOT / "build/packages/ziran/include"),
                        "-I" + str(ROOT / "build/packages/monocypher/src"),
                        "-I" + str(ROOT / "build/packages/monocypher/src/optional"),
                        str(ROOT / "tests/package_manager_host.c"),
                        *(str(path) for path in generated.rglob("*.c")),
                        str(ROOT / "build/packages/monocypher/src/monocypher.c"),
                        str(ROOT / "build/packages/monocypher/src/optional/monocypher-ed25519.c"),
                        str(ROOT / "build/ziran-toolchain/libziran.a"),
                        "-Wl,--wrap=file_download_FileDownloadStart", "-Wl,--wrap=file_download_FileDownloadPoll",
                        "-Wl,--wrap=file_download_FileDownloadRelease", "-Wl,--wrap=storage_db_path",
                        "-Wl,--wrap=SecureRandom",
                        "-Wl,--gc-sections", "-lm", "-o", str(work / "manager-test")], check=True)
        subprocess.run([str(work / "manager-test"), str(fixtures)], check=True)
    print("Signed package identity, API, canonical metadata, payload and nested-dependency and update lifecycle tests passed")


if __name__ == "__main__":
    main()
