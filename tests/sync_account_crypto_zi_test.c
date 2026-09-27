#include "account_types.h"
#include "storage/sync_crypto.h"
#include "storage/sync_account_text.h"
#include "storage/sync_account_parse.h"
#include "storage/sync_account_encrypted.h"
#include "storage/sync_crypto_random.h"

#include <oqs/oqs.h>
#include <stdio.h>
#include <string.h>

int32_t CreateSyncAccount(SyncAccount *account);
int32_t SignSyncAccountHex(SyncAccount *account, uint8_t *message,
                           int64_t message_length, uint8_t *output,
                           int64_t output_size);

String
app_text_from_cstring(uint8_t *data, int32_t capacity)
{
    size_t length = 0;
    if(data == NULL || capacity <= 0)
        return StringView("", 0);
    while(length < (size_t)capacity && data[length] != 0)
        length++;
    return StringView((const char *)data, length);
}

int
main(void)
{
    SyncAccount account = {0};
    uint8_t public_key[1312];
    uint8_t private_key[2560];
    uint8_t expected_id[65];
    uint8_t signature[2420];
    uint8_t signature_hex[4841];
    size_t signature_length = 0;
    uint8_t message[] = "Inbe account keypair";
    uint8_t random_a[32];
    uint8_t random_b[32];
    uint8_t exported[8200];
    char expected_export[8200];
    char legacy_export[8200];
    char json_export[8200];
    uint8_t encrypted_export[17664];
    uint8_t known_salt[16];
    uint8_t derived_key[32];
    uint8_t derived_hex[65];
    int expected_length;
    SyncAccount imported = {0};
    OQS_SIG *scheme;

    if(!SyncCryptoRandom(random_a, sizeof(random_a)) ||
       !SyncCryptoRandom(random_b, sizeof(random_b)) ||
       memcmp(random_a, random_b, sizeof(random_a)) == 0 ||
       SyncCryptoRandom(NULL, 1) || SyncCryptoRandom(random_a, -1)) {
        fputs("secure random source failed\n", stderr);
        return 1;
    }
    SyncCryptoWipe(random_a, sizeof(random_a));
    for(size_t index = 0; index < sizeof(random_a); index++) {
        if(random_a[index] != 0) {
            fputs("secure key wipe failed\n", stderr);
            return 1;
        }
    }

    if(!CreateSyncAccount(&account)) {
        fputs("could not create account\n", stderr);
        return 1;
    }
    if(strlen((const char *)account.public_id) != 64 ||
       strlen((const char *)account.public_key_hex) != 2624 ||
       strlen((const char *)account.private_key_hex) != 5120 ||
       !SyncCryptoHexToBytes(StringView((const char *)account.public_key_hex, 2624),
                             public_key, sizeof(public_key)) ||
       !SyncCryptoHexToBytes(StringView((const char *)account.private_key_hex, 5120),
                             private_key, sizeof(private_key))) {
        fputs("account key lengths or encoding are invalid\n", stderr);
        return 1;
    }
    SyncCryptoSha256Hex(public_key, sizeof(public_key), expected_id);
    if(strcmp((const char *)account.public_id, (const char *)expected_id) != 0) {
        fputs("account ID does not match the public key\n", stderr);
        return 1;
    }

    expected_length = snprintf(expected_export, sizeof(expected_export),
        "account-key-v1\nalgorithm=ML-DSA-44\npublic_id=%s\npublic_key=%s\nprivate_key=%s\n",
        account.public_id, account.public_key_hex, account.private_key_hex);
    if(expected_length <= 0 || (size_t)expected_length >= sizeof(expected_export) ||
       !ExportSyncAccountText(&account, exported, sizeof(exported)) ||
       strcmp((const char *)exported, expected_export) != 0) {
        fputs("account export wire format is invalid\n", stderr);
        return 1;
    }
    if(ExportSyncAccountText(&account, exported, expected_length) || exported[0] != 0) {
        fputs("account export accepted a truncated buffer\n", stderr);
        return 1;
    }
    if(!ParseSyncAccountText(StringView(expected_export, expected_length), &imported) ||
       memcmp(&account, &imported, sizeof(account)) != 0) {
        fputs("account export could not be imported\n", stderr);
        return 1;
    }
    if(snprintf(legacy_export, sizeof(legacy_export),
        "\xef\xbb\xbfksync-account-key-v1\npublic_key= %s \r\nsecret_key=%s\n",
        account.public_key_hex, account.private_key_hex) >= (int)sizeof(legacy_export) ||
       !ParseSyncAccountText(StringView(legacy_export, strlen(legacy_export)), &imported) ||
       memcmp(&account, &imported, sizeof(account)) != 0) {
        fputs("legacy account key could not be imported\n", stderr);
        return 1;
    }
    {
        size_t used = 0;
        const char *cursor = expected_export;
        memcpy(json_export, "{\"exported_key\":\"", 17);
        used = 17;
        while(*cursor != '\0' && used + 3 < sizeof(json_export)) {
            if(*cursor == '\n') {
                json_export[used++] = '\\';
                json_export[used++] = 'n';
            } else {
                json_export[used++] = *cursor;
            }
            cursor++;
        }
        json_export[used++] = '"';
        json_export[used++] = '}';
        if(*cursor != '\0' ||
           !ParseSyncAccountText(StringView(json_export, used), &imported) ||
           memcmp(&account, &imported, sizeof(account)) != 0) {
            fputs("JSON account key could not be imported\n", stderr);
            return 1;
        }
    }
    {
        char *id = strstr(expected_export, "public_id=");
        if(id == NULL) return 1;
        id += strlen("public_id=");
        id[0] = id[0] == 'a' ? 'b' : 'a';
        if(ParseSyncAccountText(StringView(expected_export, expected_length), &imported) ||
           imported.private_key_hex[0] != 0) {
            fputs("tampered account ID was accepted\n", stderr);
            return 1;
        }
    }
    for(size_t index = 0; index < sizeof(known_salt); index++)
        known_salt[index] = (uint8_t)index;
    if(!AccountDerivePassphraseKey(StringView("correct horse battery staple", 28),
                                   known_salt, derived_key, 600000) ||
       !SyncCryptoBytesToHex(derived_key, sizeof(derived_key),
                             derived_hex, sizeof(derived_hex)) ||
       strcmp((const char *)derived_hex,
              "518d61c1817a98f43a5800808ed0393cfd69d67a9b30d9283dbc1e593e05ca05") != 0) {
        fputs("legacy encrypted key derivation changed\n", stderr);
        return 1;
    }
    if(!ExportSyncAccountTextEncrypted(&account,
        StringView("correct horse battery staple", 28),
        encrypted_export, sizeof(encrypted_export)) ||
       !ParseSyncAccountTextEncrypted(
           StringView((const char *)encrypted_export,
                      strlen((const char *)encrypted_export)),
           StringView("correct horse battery staple", 28), &imported) ||
       memcmp(&account, &imported, sizeof(account)) != 0) {
        fputs("encrypted account key round trip failed\n", stderr);
        return 1;
    }
    if(ParseSyncAccountTextEncrypted(
           StringView((const char *)encrypted_export,
                      strlen((const char *)encrypted_export)),
           StringView("wrong passphrase", 16), &imported) ||
       imported.private_key_hex[0] != 0) {
        fputs("encrypted key accepted a wrong passphrase\n", stderr);
        return 1;
    }
    {
        size_t length = strlen((const char *)encrypted_export);
        encrypted_export[length - 1] = encrypted_export[length - 1] == 'a' ? 'b' : 'a';
        if(ParseSyncAccountTextEncrypted(
               StringView((const char *)encrypted_export, length),
               StringView("correct horse battery staple", 28), &imported) ||
           imported.private_key_hex[0] != 0) {
            fputs("encrypted key accepted tampered ciphertext\n", stderr);
            return 1;
        }
    }

    scheme = OQS_SIG_new("ML-DSA-44");
    if(scheme == NULL || scheme->length_public_key != sizeof(public_key) ||
       scheme->length_secret_key != sizeof(private_key) ||
       scheme->length_signature != sizeof(signature)) {
        fputs("ML-DSA-44 sizes changed\n", stderr);
        OQS_SIG_free(scheme);
        return 1;
    }
    if(OQS_SIG_sign(scheme, signature, &signature_length,
                    message, sizeof(message) - 1, private_key) != OQS_SUCCESS ||
       signature_length != sizeof(signature) ||
       OQS_SIG_verify(scheme, message, sizeof(message) - 1,
                      signature, signature_length, public_key) != OQS_SUCCESS) {
        fputs("account keypair could not sign and verify\n", stderr);
        OQS_SIG_free(scheme);
        return 1;
    }
    if(!SignSyncAccountHex(&account, message, sizeof(message) - 1,
                           signature_hex, sizeof(signature_hex)) ||
       !SyncCryptoHexToBytes(StringView((const char *)signature_hex, 4840),
                             signature, sizeof(signature)) ||
       OQS_SIG_verify(scheme, message, sizeof(message) - 1,
                      signature, sizeof(signature), public_key) != OQS_SUCCESS) {
        fputs("Ziran account signature did not verify\n", stderr);
        OQS_SIG_free(scheme);
        return 1;
    }
    if(SignSyncAccountHex(&account, message, sizeof(message) - 1,
                          signature_hex, 4840) || signature_hex[0] != 0) {
        fputs("signature accepted a truncated buffer\n", stderr);
        OQS_SIG_free(scheme);
        return 1;
    }
    message[0] ^= 1;
    if(OQS_SIG_verify(scheme, message, sizeof(message) - 1,
                      signature, signature_length, public_key) == OQS_SUCCESS) {
        fputs("tampered message verified\n", stderr);
        OQS_SIG_free(scheme);
        return 1;
    }
    OQS_SIG_free(scheme);
    puts("Inbe Ziran ML-DSA-44 account and encrypted key backup passed");
    return 0;
}
