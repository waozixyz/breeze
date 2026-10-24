#!/usr/bin/env python3
"""Write tests/fixtures/photos-2.1.43.sql: a profile as Inbe 2.1.43 left it.

Released versions kept Diary photos as Diary files and the media library in
private.inbe.v1.media, each photo's bytes as one old sealed copy at
/api/v1/blobs/inbe/ (src/cells/diary_records.zi). The fixture holds that
profile's database rows and, in fixture_node_blobs, the old copies its two
nodes hold. Its tables are Inbe 1.8.9's (schema-1.8.9.sql) with the
sync_record_copies and diary_blobs tables of 2.1.43; the upgrade adds the
rest, as it does for any older profile. tests/entity_photos_behavior.zi writes the photos' files from
the same byte pattern (FixturePhoto) and upgrades the profile.

Photos: walk (a Diary photo with an old copy, also in the library), tea (a
Diary photo never uploaded), rain (a Diary photo from before copies, kept
as hex chunks), lake (a library photo in Trash whose original is only on
the node, with a preview here), orphan (a Diary file no entry includes).
"""

import hashlib
import hmac
import json
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

USER = "fixture-user"
ACCOUNT = "7e1d" * 16
PRIVATE_KEY_HEX = "42" * 2560
SYNC_NODE = "https://sync.photos.test"
OTHER_NODE = "https://other.photos.test"
CHUNK = 1024


def photo(size: int, seed: int) -> bytes:
    """PNG's signature, then (index * 7 + seed) % 251, as FixturePhoto."""
    header = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    return bytes(header[index] if index < 8 else (index * 7 + seed) % 251 for index in range(size))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def old_copy(data: bytes) -> tuple[str, str, bytes]:
    """A released version's sealed copy: its address, its key and its bytes."""
    private = bytes.fromhex(PRIVATE_KEY_HEX)
    master = hmac.new(private, b"inbe-diary-blob-key-v1", hashlib.sha256).digest()
    key = hmac.new(master, sha(data).encode(), hashlib.sha256).digest()
    sealed = ChaCha20Poly1305(key).encrypt(bytes(12), data, b"inbe.diary.blob.v1")
    return sha(sealed), key.hex(), sealed


def quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


class Fixture:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.clock = 1792000000

    def setting(self, key: str, value: str) -> None:
        self.clock += 1
        self.lines.append(f"INSERT INTO settings VALUES({quote(USER)},{quote(key)},{quote(value)},{self.clock});")

    def document(self, name: str, document: dict) -> None:
        """A day's document as hex chunks beside its entry (DiaryRecordSave)."""
        data = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode()
        self.chunks(sha(data), data)
        count = (len(data) + CHUNK - 1) // CHUNK
        self.setting(f"cell.diary.file.{name}",
                     json.dumps({"hash": sha(data), "count": count, "size": len(data)}, separators=(",", ":")))

    def chunks(self, digest: str, data: bytes) -> None:
        for index in range(0, (len(data) + CHUNK - 1) // CHUNK):
            self.setting(f"cell.diary.chunk.{digest}.{index}", data[index * CHUNK:(index + 1) * CHUNK].hex())

    def node_blob(self, node: str, address: str, sealed: bytes) -> None:
        self.lines.append(f"INSERT INTO fixture_node_blobs VALUES({quote(node)},{quote(address)},{quote(sealed.hex())});")

    def known(self, node: str, address: str) -> None:
        self.lines.append(f"INSERT INTO diary_blobs VALUES({quote(node)},{quote(address)});")


def main() -> None:
    walk = photo(2600, 11)
    tea = photo(2700, 12)
    rain = photo(2500, 9)
    lake = photo(2900, 14)
    lake_preview = photo(900, 21)
    orphan = photo(2800, 13)
    fixture = Fixture()
    schema = Path(__file__).with_name("schema-1.8.9.sql").read_text()
    out = [schema.rstrip(),
           "CREATE TABLE IF NOT EXISTS sync_record_copies( collection TEXT NOT NULL, id TEXT NOT NULL, json TEXT NOT NULL, PRIMARY KEY(collection,id));",
           "CREATE TABLE IF NOT EXISTS diary_blobs( node TEXT NOT NULL, blob TEXT NOT NULL, PRIMARY KEY(node,blob));",
           "CREATE TABLE fixture_node_blobs(node TEXT NOT NULL, address TEXT NOT NULL, bytes TEXT NOT NULL);"]
    fixture.lines.append(f"INSERT INTO users VALUES({quote(USER)},1,'local');")
    fixture.lines.append(f"INSERT INTO meta VALUES('current_user_id',{quote(USER)});")
    fixture.setting("sync_private_key", PRIVATE_KEY_HEX)
    fixture.setting("sync_public_key", "fixture-public-key")
    fixture.setting("sync_public_id", ACCOUNT)
    fixture.setting("sync_server_url", SYNC_NODE)
    fixture.setting("sync_enabled", "1")

    walk_address, walk_key, walk_sealed = old_copy(walk)
    fixture.setting("cell.diary.file.photo-20240402081500-1.bin", json.dumps(
        {"hash": sha(walk), "size": len(walk), "blob": walk_address, "key": walk_key}, separators=(",", ":")))
    fixture.setting("cell.diary.file.photo-20240403090000-1.bin",
                    json.dumps({"hash": sha(tea), "size": len(tea)}, separators=(",", ":")))
    fixture.chunks(sha(rain), rain)
    fixture.setting("cell.diary.file.photo-20240301000000-1.bin", json.dumps(
        {"hash": sha(rain), "count": 3, "size": len(rain)}, separators=(",", ":")))
    orphan_address, orphan_key, orphan_sealed = old_copy(orphan)
    fixture.setting("cell.diary.file.photo-20240405000000-1.bin", json.dumps(
        {"hash": sha(orphan), "size": len(orphan), "blob": orphan_address, "key": orphan_key}, separators=(",", ":")))
    fixture.document("2024-04-02.json", {"version": 1, "date": "2024-04-02", "text": "Walk",
                                         "photos": [{"file": "photo-20240402081500-1.bin", "name": "IMG_2041.png"}]})
    fixture.document("2024-04-03.json", {"version": 1, "date": "2024-04-03",
                                         "text": "Tea\n\n![Tea cup](diary:photo-20240403090000-1.bin)", "photos": []})
    fixture.document("2024-04-04.json", {"version": 1, "date": "2024-04-04", "text": "Rain",
                                         "photos": [{"file": "photo-20240301000000-1.bin", "name": "Rain"}]})

    # The library: walk joined it from the Diary and shares its old copy;
    # lake was added in Photos and moved to Trash.
    fixture.setting(f"cell.media.{sha(walk)}", json.dumps(
        {"hash": sha(walk), "size": len(walk), "type": "png", "name": "IMG_2041.png", "day": "2024-04-02",
         "taken": "2024-04-02", "added": 1792000100, "capture": 0, "trashed": 0,
         "blob": walk_address, "key": walk_key}, separators=(",", ":")))
    lake_address, lake_key, lake_sealed = old_copy(lake)
    preview_address, preview_key, preview_sealed = old_copy(lake_preview)
    fixture.setting(f"cell.media.{sha(lake)}", json.dumps(
        {"hash": sha(lake), "size": len(lake), "type": "png", "name": "Lake.png", "day": "2024-05-01",
         "taken": "2024-05-01T10:00:00+02:00", "added": 1792000200, "capture": 1, "trashed": 1,
         "blob": lake_address, "key": lake_key}, separators=(",", ":")))
    fixture.setting(f"cell.media.preview.{sha(lake)}", json.dumps(
        {"hash": sha(lake_preview), "size": len(lake_preview), "type": "png",
         "blob": preview_address, "key": preview_key}, separators=(",", ":")))

    for address, sealed in ((walk_address, walk_sealed), (lake_address, lake_sealed),
                            (preview_address, preview_sealed), (orphan_address, orphan_sealed)):
        fixture.node_blob(SYNC_NODE, address, sealed)
        fixture.known(SYNC_NODE, address)
    fixture.node_blob(OTHER_NODE, walk_address, walk_sealed)
    fixture.known(OTHER_NODE, walk_address)

    out.extend(fixture.lines)
    header = ("-- An Inbe 2.1.43 profile with photos, made by make_photos_fixture.py.\n"
              "-- Do not edit; change the script and run it again.\n")
    Path(__file__).with_name("photos-2.1.43.sql").write_text(header + "\n".join(out) + "\n")


if __name__ == "__main__":
    main()
