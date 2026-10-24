#!/usr/bin/env python3
"""Print the known-answer entity record of tests/storage_sync_behavior.zi.

The record is sealed with libsodium (PyNaCl), as other apps of the account
seal theirs, in Daochi's record profile (docs/entity-data.md): the record
key of kind photos from the test account's private key, XChaCha20-Poly1305
with a fixed nonce, and the profile's sorted-key envelope, base64url without
padding. Run it to reproduce the constants the test embeds.
"""

import base64
import hashlib
import hmac
import json

import nacl.bindings

# set_account() stores the private key as the hex digits "42" repeated.
PRIVATE_KEY = bytes([0x42]) * 2560
ACCOUNT = "7e1d" * 16
HASH = "1f2e3d4c5b6a7988" * 4
COLLECTION = "private.entity.v1.photos"
SCHEMA = "entity.photo.v1"
NONCE = bytes(range(24))


def base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> None:
    key = hmac.new(PRIVATE_KEY, b"daochi-entity-v1/records/photos", hashlib.sha256).digest()
    plain = json.dumps({"hash": HASH, "size": 6000, "type": "image/jpeg", "taken_at": 1792224900,
                        "width": 4032, "height": 3024, "added_at": 1792224960,
                        "name": "IMG_2041.jpg", "caption": "Written by another app"},
                       separators=(",", ":"), sort_keys=True)
    aad = ('{"account_id":"%s","app_id":"entity","collection":"%s","id":"%s","schema":"%s"}'
           % (ACCOUNT, COLLECTION, HASH, SCHEMA))
    sealed = nacl.bindings.crypto_aead_xchacha20poly1305_ietf_encrypt(
        plain.encode(), aad.encode(), NONCE, key)
    envelope = ('{"aad":%s,"alg":"xchacha20poly1305","ciphertext":"%s","key_id":"entity-v1",'
                '"nonce":"%s","profile":"daochi-record-v1"}' % (aad, base64url(sealed), base64url(NONCE)))
    print("record key:", key.hex())
    print("plain:", plain)
    print("nonce:", base64url(NONCE))
    print("ciphertext:", base64url(envelope.encode()))


if __name__ == "__main__":
    main()
