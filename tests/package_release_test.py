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
import argparse
import re
import shutil
from io import BytesIO
from urllib.error import HTTPError

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("inbe_release", ROOT / "scripts/package-release.py")
release_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_tool)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain', type=Path)
    parser.add_argument('--module-map', type=Path)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--bundle-build-dir', type=Path, default=ROOT / 'build')
    options = parser.parse_args()
    work = ROOT / "build/package-release-test"
    work.mkdir(parents=True, exist_ok=True)
    toolchain = options.toolchain or ROOT / 'build/packages/ziran'
    runtime = options.runtime or ROOT / 'build/ziran-toolchain/libziran.a'
    def stage(*arguments):
        return release_tool.stage(*arguments, build_directory=options.bundle_build_dir)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')}
    if options.module_map:
        rows = options.module_map.read_text().splitlines()
        for name in ('package_release_behavior', 'package_manager_behavior'):
            rows.append(f'M\troot\t{name}\t{ROOT / "tests" / (name + ".zi")}')
        mapping = work / 'module-map.tsv'
        mapping.write_text('\n'.join(dict.fromkeys(rows)) + '\n')
        environment['ZIRAN_PACKAGE_MAP'] = str(mapping.resolve())

    # Dependencies are imported as PACKAGE/Module through their linked packages.
    package_paths = subprocess.check_output(
        ['sh', str(ROOT / 'scripts/package-paths.sh'), str(ROOT / 'build/packages')],
        text=True).split()[1::2]

    def generate(target, fixture, paths):
        if target.exists():
            shutil.rmtree(target)
        if options.module_map:
            command = [str(toolchain / 'build/bin/zi2c')]
        else:
            command = [str(ROOT / 'build/ziran-toolchain/bin/ziran'), 'build', '--target=c']
        subprocess.run([*command, '--no-main', '--root', str(ROOT / 'tests'),
                        *[argument for path in paths for argument in ('--module-path', str(path))],
                        '-o', str(target), str(ROOT / 'tests' / fixture)], env=environment, check=True)
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
        values = stage(store, private, "test-key", publishers)
        stage(store, private, "test-key", publishers)  # idempotent

        paid = {pack["sha256"] + ".zib" for pack in release_tool.stored_practice_packs(store)
                if pack.get("product")}

        def served(url, timeout, paid_public=False):
            assert timeout == 30
            prefix = "https://node.example/api/v2/packages/"
            assert url.startswith(prefix)
            app_id, filename = url.removeprefix(prefix).split("/")
            # Without the node's grant a paid pack is refused.
            if app_id == "inbe.practices" and filename in paid and not paid_public:
                raise HTTPError(url, 403, "Forbidden", {}, None)
            # The publisher asks as bucket 0, which receives staged releases first.
            if filename.startswith("latest"):
                assert filename == "latest?bucket=0", filename
                filename = "latest-v2.json"
            return BytesIO((store / app_id / filename).read_bytes())

        release_tool.verify_origin(store, "https://node.example", served)
        for failure in ("metadata", "hash", "truncated", "oversized") + (("paid-public",) if paid else ()):
            def damaged(url, timeout):
                content = served(url, timeout, failure == "paid-public").read()
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
        # The node gates each paid pack by the marker the importer writes.
        markers = sorted(store.glob("inbe.practices/*.zib.product"))
        assert markers
        for marker in markers:
            assert (remote / marker.relative_to(store)).read_bytes() == marker.read_bytes()
        unmarked = fixtures / "unmarked-upload"
        unmarked.mkdir()
        with tarfile.open(unmarked / "packages.tar", "w") as tar:
            for path in sorted(store.rglob("*")):
                if path.is_file() and path.name != ".publish.lock" and path != markers[0]:
                    tar.add(path, arcname=str(path.relative_to(store)))
        try:
            release_tool.import_archive(unmarked / "packages.tar", fixtures / "unmarked-remote", publishers)
        except ValueError:
            pass
        else:
            raise AssertionError("a paid pack without its product marker was accepted")
        assert not (fixtures / "unmarked-remote" / markers[0].relative_to(store).with_suffix("")).exists()
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
            stage(older, private, "test-key", publishers)
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
        root_data = (options.bundle_build_dir / "inbe.zib").read_bytes()
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
        data = (options.bundle_build_dir / "cells/habits.zib").read_bytes()
        (fixtures / "habits-bytes").write_bytes(data)
        (fixtures / "corrupt-bytes").write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        (fixtures / "diary-bytes").write_bytes((options.bundle_build_dir / "cells/diary.zib").read_bytes())
        updated = json.loads(json.dumps(values["diary"]))
        diary_version = list(map(int, updated["version"].split(".")))
        diary_version[2] += 1
        updated.update(sequence=updated["sequence"] + 1, version=".".join(map(str, diary_version)))
        updated["signature"] = key.sign(release_tool.signing_message(updated)).hex()
        (fixtures / "diary-new").write_text(json.dumps(updated))
        older = json.loads(json.dumps(values["diary"]))
        older.update(sequence=older["sequence"] - 1, version="1.2.9")
        older["signature"] = key.sign(release_tool.signing_message(older)).hex()
        history = dict(versions=[updated, values["diary"], older])
        (fixtures / "diary-history").write_text(json.dumps(history))
        (fixtures / "diary-history-many").write_text(json.dumps(dict(versions=history["versions"] + [older])))
        (fixtures / "diary-history-order").write_text(json.dumps(dict(versions=list(reversed(history["versions"])))))
        (fixtures / "diary-history-owner").write_text(json.dumps(dict(versions=[values["habits"]])))
        bad_history = json.loads(json.dumps(history))
        bad_history["versions"][1]["version"] = "0.0.1"
        (fixtures / "diary-history-forged").write_text(json.dumps(bad_history))
        diary_version[2] += 1
        updated["version"] = ".".join(map(str, diary_version))
        (fixtures / "diary-bad").write_text(json.dumps(updated))
        generate(work / 'generated', 'package_release_behavior.zi',
                 [ROOT / 'src', toolchain / 'std', ROOT / 'build/packages/kryon/src/ui',
                  ROOT / 'build/packages/daochi-client', *package_paths])
        sources = list((work / "generated").rglob("*.c"))
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-D_GNU_SOURCE", "-O1",
                        "-ffunction-sections", "-fdata-sections", "-I" + str(work / "generated"),
                        "-I" + str(toolchain / "include"),
                        "-I" + str(ROOT / "build/packages/monocypher/src"),
                        "-I" + str(ROOT / "build/packages/monocypher/src/optional"),
                        str(ROOT / "tests/package_release_host.c"), *(str(path) for path in sources),
                        str(ROOT / "build/packages/monocypher/src/monocypher.c"),
                        str(ROOT / "build/packages/monocypher/src/optional/monocypher-ed25519.c"),
                        str(runtime), "-Wl,--gc-sections", "-lm",
                        "-o", str(work / "test")], check=True)
        subprocess.run([str(work / "test"), str(fixtures)], env=environment, check=True)
        generated = work / "manager"
        generate(generated, 'package_manager_behavior.zi',
                 [ROOT / 'src', toolchain / 'std', ROOT / 'build/packages/kryon/src/ui',
                  ROOT / 'build/packages/kryon/src/backend', ROOT / 'build/packages/daochi-client',
                  ROOT / 'build/packages/kss/src', ROOT / 'build/packages/game2d/src',
                  *package_paths])
        # Package scoping changes generated C names, not the download API.
        # Bind this fixture's wrappers to the actual declared symbols.
        wrappers = []
        for name in ('Start', 'Poll', 'Release'):
            legacy = 'file_download_FileDownload' + name
            symbol = legacy
            if options.module_map:
                header = next(generated.glob('*file_download.h')).read_text()
                symbol = re.search(r'(\w*file_download_FileDownload' + name + r')\(', header)[1]
            wrappers.extend(('-D__wrap_' + legacy + '=__wrap_' + symbol, '-Wl,--wrap=' + symbol))
        subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-D_GNU_SOURCE", "-O1",
                        "-ffunction-sections", "-fdata-sections", "-I" + str(generated),
                        "-I" + str(toolchain / "include"),
                        "-I" + str(ROOT / "build/packages/monocypher/src"),
                        "-I" + str(ROOT / "build/packages/monocypher/src/optional"),
                        str(ROOT / "tests/package_manager_host.c"),
                        *(str(path) for path in generated.rglob("*.c")),
                        str(ROOT / "build/packages/monocypher/src/monocypher.c"),
                        str(ROOT / "build/packages/monocypher/src/optional/monocypher-ed25519.c"),
                        str(runtime), *wrappers, "-Wl,--wrap=storage_db_path", "-Wl,--wrap=storage_user_id_buffer",
                        "-Wl,--wrap=SecureRandom",
                        "-Wl,--gc-sections", "-lm", "-o", str(work / "manager-test")], check=True)
        subprocess.run([str(work / "manager-test"), str(fixtures)], env=environment, check=True)
    print("Signed package identity, API, canonical metadata, payload and nested-dependency and update lifecycle tests passed")


if __name__ == "__main__":
    main()
