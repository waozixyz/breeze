#include "storage/sync_crypto.h"
#include "storage/sync_crypto_hmac.h"
#include "storage/sync_crypto_chacha.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct HashCase {
    size_t length;
    const char *expected;
} HashCase;

static int
check_hash(const uint8_t *data, size_t length, const char *expected)
{
    uint8_t hex[65];

    SyncCryptoSha256Hex((uint8_t *)data, (int64_t)length, hex);
    if(strcmp((const char *)hex, expected) != 0) {
        fprintf(stderr, "SHA-256 mismatch at %zu bytes: %s\n", length, hex);
        return 0;
    }
    return 1;
}

static int
check_aead_case(size_t plain_length, size_t aad_length, const char *expected)
{
    uint8_t key[32];
    uint8_t nonce[12];
    uint8_t plain[65];
    uint8_t aad[17];
    uint8_t sealed[81];
    uint8_t opened[65];
    uint8_t hex[163];

    for(size_t index = 0; index < sizeof(key); index++)
        key[index] = (uint8_t)index;
    for(size_t index = 0; index < sizeof(nonce); index++)
        nonce[index] = (uint8_t)index;
    for(size_t index = 0; index < sizeof(plain); index++)
        plain[index] = (uint8_t)index;
    for(size_t index = 0; index < sizeof(aad); index++)
        aad[index] = (uint8_t)index;
    if(!SyncCryptoChaCha20Poly1305Seal(key, nonce, plain, plain_length,
                                       aad, aad_length, sealed, sizeof(sealed)) ||
       !SyncCryptoBytesToHex(sealed, plain_length + 16, hex, sizeof(hex)) ||
       strcmp((const char *)hex, expected) != 0 ||
       !SyncCryptoChaCha20Poly1305Open(key, nonce, sealed, plain_length + 16,
                                       aad, aad_length, opened, sizeof(opened)) ||
       memcmp(opened, plain, plain_length) != 0) {
        fprintf(stderr, "ChaCha20-Poly1305 boundary vector failed: %zu/%zu\n",
                plain_length, aad_length);
        return 0;
    }
    return 1;
}

int
main(void)
{
    static const HashCase cases[] = {
        {0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        {55, "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318"},
        {56, "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a"},
        {63, "7d3e74a05d7db15bce4ad9ec0658ea98e3f06eeecf16b4c6fff2da457ddc2f34"},
        {64, "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"},
        {65, "635361c48bb9eab14198e76ea8ab7f1a41685d6ad62aa9146d301d4f17eb0ae0"},
        {1000, "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3"},
        {1000000, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"},
    };
    uint8_t *payload = malloc(1000000);
    uint8_t raw[3] = {0, 255, 16};
    uint8_t encoded[7];
    uint8_t decoded[3] = {0};
    uint8_t short_output[6];
    uint8_t digest[32];
    uint8_t digest_hex[65];
    uint8_t hmac_key[20];
    uint8_t long_key[100];
    uint8_t long_salt[36];
    char long_password[100];
    uint8_t aead_key[32];
    uint8_t nonce[12];
    uint8_t aad[12];
    uint8_t sealed[130];
    uint8_t opened[114];
    uint8_t sealed_hex[261];
    uint8_t zero_key[32] = {0};
    uint8_t zero_nonce[12] = {0};
    const char *aead_plain =
        "Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it.";

    if(payload == NULL)
        return 1;
    memset(payload, 'a', 1000000);
    if(!check_hash(NULL, 0, cases[0].expected) ||
       !check_hash((const uint8_t *)"abc", 3,
                   "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"))
        return 1;
    for(size_t index = 1; index < sizeof(cases) / sizeof(cases[0]); index++) {
        if(!check_hash(payload, cases[index].length, cases[index].expected))
            return 1;
    }
    free(payload);

    if(!SyncCryptoBytesToHex(raw, 3, encoded, sizeof(encoded)) ||
       strcmp((const char *)encoded, "00ff10") != 0)
        return 1;
    short_output[0] = 'x';
    if(SyncCryptoBytesToHex(raw, 3, short_output, sizeof(short_output)) ||
       short_output[0] != 0)
        return 1;
    if(!SyncCryptoHexToBytes(StringView("00Ff10", 6), decoded, 3) ||
       memcmp(decoded, raw, 3) != 0)
        return 1;
    if(SyncCryptoHexToBytes(StringView("00fg10", 6), decoded, 3) ||
       SyncCryptoHexToBytes(StringView("00ff", 4), decoded, 3))
        return 1;

    memset(hmac_key, 0x0b, sizeof(hmac_key));
    if(!SyncCryptoHmacSha256(hmac_key, sizeof(hmac_key),
                             (uint8_t *)"Hi There", 8, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7") != 0) {
        fputs("HMAC-SHA-256 RFC vector failed\n", stderr);
        return 1;
    }
    if(!SyncCryptoHmacSha256Text(hmac_key, sizeof(hmac_key),
                                 StringView("Hi There", 8), digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7") != 0) {
        fputs("HMAC-SHA-256 Ziran string path failed\n", stderr);
        return 1;
    }
    for(size_t index = 0; index < sizeof(long_key); index++)
        long_key[index] = (uint8_t)index;
    if(!SyncCryptoHmacSha256(long_key, sizeof(long_key),
                             (uint8_t *)"Inbe long HMAC key", 18, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "24f4d381b586bcf153db89735ebbe9b925f731d4350d079e92a68887a0d854df") != 0) {
        fputs("HMAC-SHA-256 long key failed\n", stderr);
        return 1;
    }
    if(!SyncCryptoPbkdf2Sha256((uint8_t *)"password", 8,
                                (uint8_t *)"salt", 4, 1, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b") != 0) {
        fputs("PBKDF2-SHA-256 first round failed\n", stderr);
        return 1;
    }
    if(!SyncCryptoPbkdf2Sha256Text(StringView("password", 8),
                                    (uint8_t *)"salt", 4, 1, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b") != 0) {
        fputs("PBKDF2-SHA-256 Ziran string path failed\n", stderr);
        return 1;
    }
    if(!SyncCryptoPbkdf2Sha256((uint8_t *)"password", 8,
                                (uint8_t *)"salt", 4, 4096, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a") != 0) {
        fputs("PBKDF2-SHA-256 repeated rounds failed\n", stderr);
        return 1;
    }
    for(size_t index = 0; index < sizeof(long_salt); index++)
        long_salt[index] = (uint8_t)index;
    if(!SyncCryptoPbkdf2Sha256((uint8_t *)"password", 8,
                                long_salt, sizeof(long_salt), 4, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "16818d27cc7f2d3c24ce34b77a74a64c3e4b23b07b818d2ee42e5df6d5916815") != 0 ||
       SyncCryptoPbkdf2Sha256((uint8_t *)"password", 8,
                               long_salt, sizeof(long_salt), 0, digest)) {
        fputs("PBKDF2-SHA-256 legacy salt or invalid rounds failed\n", stderr);
        return 1;
    }
    memset(long_password, 'p', sizeof(long_password));
    if(!SyncCryptoPbkdf2Sha256Text(
           StringView(long_password, sizeof(long_password)),
           long_salt, sizeof(long_salt), 3, digest) ||
       !SyncCryptoBytesToHex(digest, sizeof(digest), digest_hex, sizeof(digest_hex)) ||
       strcmp((const char *)digest_hex,
              "4b32eab90d1bee01e6db87c15c8ca68e48264c17af6f42d1cbad1c7d4b5da7cc") != 0) {
        fputs("PBKDF2-SHA-256 long passphrase failed\n", stderr);
        return 1;
    }

    for(size_t index = 0; index < sizeof(aead_key); index++)
        aead_key[index] = (uint8_t)(0x80 + index);
    if(!SyncCryptoHexToBytes(StringView("070000004041424344454647", 24),
                             nonce, sizeof(nonce)) ||
       !SyncCryptoHexToBytes(StringView("50515253c0c1c2c3c4c5c6c7", 24),
                             aad, sizeof(aad)) ||
       strlen(aead_plain) != sizeof(opened) ||
       !SyncCryptoChaCha20Poly1305Seal(aead_key, nonce,
           (uint8_t *)aead_plain, sizeof(opened), aad, sizeof(aad),
           sealed, sizeof(sealed)) ||
       !SyncCryptoBytesToHex(sealed, sizeof(sealed),
                             sealed_hex, sizeof(sealed_hex)) ||
       strcmp((const char *)sealed_hex,
           "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d63dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b3692ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc3ff4def08e4b7a9de576d26586cec64b61161ae10b594f09e26a7e902ecbd0600691") != 0) {
        fputs("ChaCha20-Poly1305 RFC vector failed\n", stderr);
        return 1;
    }
    memset(opened, 0xa5, sizeof(opened));
    if(!SyncCryptoChaCha20Poly1305Open(aead_key, nonce,
                                       sealed, sizeof(sealed), aad, sizeof(aad),
                                       opened, sizeof(opened)) ||
       memcmp(opened, aead_plain, sizeof(opened)) != 0) {
        fputs("ChaCha20-Poly1305 decrypt failed\n", stderr);
        return 1;
    }
    sealed[sizeof(sealed) - 1] ^= 1;
    memset(opened, 0xa5, sizeof(opened));
    if(SyncCryptoChaCha20Poly1305Open(aead_key, nonce,
                                      sealed, sizeof(sealed), aad, sizeof(aad),
                                      opened, sizeof(opened)) ||
       opened[0] != 0xa5) {
        fputs("ChaCha20-Poly1305 accepted a tampered tag\n", stderr);
        return 1;
    }
    sealed[sizeof(sealed) - 1] ^= 1;
    aad[0] ^= 1;
    if(SyncCryptoChaCha20Poly1305Open(aead_key, nonce,
                                      sealed, sizeof(sealed), aad, sizeof(aad),
                                      opened, sizeof(opened)) ||
       SyncCryptoChaCha20Poly1305Seal(aead_key, nonce,
           (uint8_t *)aead_plain, sizeof(opened), aad, sizeof(aad),
           sealed, sizeof(sealed) - 1)) {
        fputs("ChaCha20-Poly1305 accepted changed AAD or short output\n", stderr);
        return 1;
    }
    if(!SyncCryptoChaCha20Poly1305Seal(zero_key, zero_nonce,
                                       NULL, 0, NULL, 0, sealed, 16) ||
       !SyncCryptoBytesToHex(sealed, 16, sealed_hex, sizeof(sealed_hex)) ||
       strcmp((const char *)sealed_hex, "4eb972c9a8fb3a1b382bb4d36f5ffad1") != 0 ||
       !SyncCryptoChaCha20Poly1305Open(zero_key, zero_nonce,
                                       sealed, 16, NULL, 0, NULL, 0)) {
        fputs("ChaCha20-Poly1305 empty input failed\n", stderr);
        return 1;
    }
    if(!check_aead_case(1, 1,
           "898a0dd79467679fc1d1c703e8c02be60f") ||
       !check_aead_case(16, 16,
           "89fa0a032d12a347bf8a35f89410006c79cc840fbc6bef68425a8233d36c12c6") ||
       !check_aead_case(65, 17,
           "89fa0a032d12a347bf8a35f89410006cd961a0f44561bbaefe8e35de69ddb823cca10ed0c23b97bf1f1b5cf349b9a10c4eb59b47c91d8eac2a81e33cac72a0e93952e5e55898e2d253b9fadea6b173a40e"))
        return 1;

    puts("Inbe Ziran sync SHA-256, HMAC, PBKDF2, ChaCha20-Poly1305, and hex passed");
    return 0;
}
