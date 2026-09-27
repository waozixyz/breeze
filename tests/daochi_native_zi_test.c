#include "storage/daochi_native.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int32_t inbe_oqs_ml_dsa_44_sign(uint8_t *signature,
                                 uint64_t *signature_length,
                                 uint8_t *message,
                                 uint64_t message_length,
                                 uint8_t *private_key)
{
    const char login[] = "daochi-sync-v1\nPOST\n/api/v1/sync/login\n";
    const char registration[] = "daochi-device-registration-v1\n";
    const char transaction[] = "daochi-tx-v1\n6\n";
    if (message_length >= sizeof login - 1 &&
        memcmp(message, login, sizeof login - 1) == 0) {
        const size_t head = sizeof login - 1;
        assert(message_length == head + 64 + 1 + 64 + 1);
        assert(message[head + 64] == '\n');
        assert(message[head + 129] == '\n');
        memcpy(signature, message + head, 64);
        memcpy(signature + 64, message + head + 65, 64);
    } else if (message_length >= sizeof registration - 1 &&
               memcmp(message, registration, sizeof registration - 1) == 0) {
        assert(strstr((const char *)message, "\ninbe\n") != NULL);
        assert(message[message_length - 1] == '\n');
    } else {
        assert(message_length >= sizeof transaction - 1);
        assert(memcmp(message, transaction, sizeof transaction - 1) == 0);
        assert(strstr((const char *)message, "\nPOST\n/api/v1/sync\n") != NULL);
        assert(message[message_length - 1] == '\n');
    }
    for (size_t index = 0; index < 2560; ++index) {
        assert(private_key[index] == 0xaa);
    }
    if (memcmp(message, login, sizeof login - 1) == 0) {
        memset(signature + 128, 0xbb, 2420 - 128);
    } else {
        memset(signature, 0xbb, 2420);
    }
    *signature_length = 2420;
    return 0;
}

int32_t inbe_oqs_random_bytes(uint8_t *output, uint64_t length)
{
    static uint8_t next = 1;
    assert(length == 32);
    memset(output, next++, length);
    return 1;
}

void OQS_MEM_cleanse(void *output, uint64_t length)
{
    memset(output, 0, length);
}

static bool sign_device(void *context, String message, Slice output)
{
    assert(context == (void *)0x1);
    assert(message.length > 200 && output.length >= 129);
    assert(memcmp(message.data, "daochi-tx-v1\n6\n", 15) == 0);
    memset(output.data, 'd', 128);
    ((char *)output.data)[128] = 0;
    return true;
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    SyncAccount account = {0};
    memset(account.public_id, 'a', 64);
    strcpy((char *)account.public_key_hex, "pub");
    memset(account.private_key_hex, 'a', 5120);
    Session session = {0};
    String base = StringView(argv[1], strlen(argv[1]));
    AuthResult result = LoginAccount(base, &account,
                                     StringLiteral("client-1"), &session);
    assert(result == AuthResult_AUTH_OK);
    assert(strcmp((char *)session.token, "token-from-server") == 0);

    assert(session.expires_in_seconds == 1800);
    assert(session.server_time == 1700000000);

    session.expires_at_local = 2000;
    char response[512];
    int32_t status = 0;
    result = RequestAccount(base, &account, StringLiteral("client-1"),
        &session, 1000, StringLiteral("GET"),
        StringLiteral("/api/v1/friends"), StringLiteral(""),
        (Slice){.data = response, .length = sizeof response}, &status);
    assert(result == AuthResult_AUTH_OK && status == 200);
    assert(strcmp(response, "{\"friends\":[]}") == 0);
    assert(strcmp((char *)session.token, "token-from-server") == 0);

    char device_id[65];
    memset(device_id, 'b', 64);
    device_id[64] = 0;
    Device device = {
        .key_id = StringView(device_id, 64),
        .public_key_hex = StringView(device_id, 64),
        .signing_context = (void *)0x1,
        .signer = sign_device,
    };
    result = SyncAccountPayload(base, &account, StringLiteral("client-1"),
        &session, device, 1001, StringLiteral("{\"protocol_version\":6}"),
        (Slice){.data = response, .length = sizeof response}, &status);
    assert(result == AuthResult_AUTH_OK && status == 200);
    assert(strcmp(response, "{\"server_version\":7}") == 0);

    result = LoginAccount(StringLiteral("http://public.example.org"),
        &account, StringLiteral("client-1"), &session);
    assert(result == AuthResult_AUTH_INVALID_URL);
    assert(session.token[0] == 0);

    result = LoginAccount(base, &account,
        StringLiteral("bad-client"), &session);
    assert(result == AuthResult_AUTH_FAILED);
    assert(session.token[0] == 0);
    puts("Inbe Daochi Ziran native adapter passed");
    return 0;
}
