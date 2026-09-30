#include "storage/device_key_store.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern int crypto_ed25519_check(const uint8_t *signature,
                                const uint8_t *public_key,
                                const uint8_t *message, size_t message_size);

static char settings[3][129];
static char scratch[129];

static int setting_index(String key)
{
    if (key.length == 23 && memcmp(key.data, "sync_device_private_key", 23) == 0)
        return 0;
    if (key.length == 22 && memcmp(key.data, "sync_device_public_key", 22) == 0)
        return 1;
    if (key.length == 18 && memcmp(key.data, "sync_device_key_id", 18) == 0)
        return 2;
    assert(!"unknown setting");
    return -1;
}

String storage_get_setting_text(String key)
{
    strcpy(scratch, settings[setting_index(key)]);
    return StringView(scratch, strlen(scratch));
}

void storage_set_setting_text(String key, String value)
{
    char *target = settings[setting_index(key)];
    assert(value.length < 129);
    memcpy(target, value.data, value.length);
    target[value.length] = 0;
}

int32_t storage_setting_text_equals(String key, String value)
{
    const char *stored = settings[setting_index(key)];
    return strlen(stored) == value.length &&
           memcmp(stored, value.data, value.length) == 0;
}

void storage_settings_begin_write(void) {}
void storage_settings_end_write(void) {}

void OQS_randombytes(uint8_t *output, size_t length)
{
    assert(length == 32);
    memset(output, 0x42, length);
}

void OQS_MEM_cleanse(void *output, size_t length)
{
    volatile uint8_t *bytes = output;
    while (length > 0) {
        *bytes++ = 0;
        --length;
    }
}

int main(void)
{
    DeviceKeyMaterial generated = {0};
    assert(GenerateDeviceKey(&generated));
    assert(strlen((char *)generated.public_hex) == 64);
    assert(strlen((char *)generated.key_id) == 64);
    char private_hex[129];
    assert(DevicePrivateHex(&generated,
        (Slice){.data = private_hex, .length = sizeof private_hex}));
    assert(strlen(private_hex) == 128);

    DeviceKeyMaterial loaded = {0};
    assert(LoadDeviceKey(StringView(private_hex, 128),
        StringView((char *)generated.public_hex, 64),
        StringView((char *)generated.key_id, 64), &loaded));
    assert(memcmp(generated.private_key, loaded.private_key, 64) == 0);
    Device device = DeviceFromKey(&loaded);
    assert(device.signer == SignDeviceMessage);
    char signature_hex[129];
    const char message[] = "daochi-tx-v1\n6\nfixture\n";
    assert(device.signer(device.signing_context,
        StringLiteral(message),
        (Slice){.data = signature_hex, .length = sizeof signature_hex}));
    uint8_t signature[64];
    assert(SyncCryptoHexToBytes(StringView(signature_hex, 128),
        signature, 64));
    assert(crypto_ed25519_check(signature, generated.public_key,
        (const uint8_t *)message, strlen(message)) == 0);

    char tampered_id[65];
    strcpy(tampered_id, (char *)generated.key_id);
    tampered_id[0] = tampered_id[0] == '0' ? '1' : '0';
    assert(!LoadDeviceKey(StringView(private_hex, 128),
        StringView((char *)generated.public_hex, 64),
        StringView(tampered_id, 64), &loaded));

    DeviceKeyMaterial persisted = {0};
    assert(LoadOrCreateDeviceKey(&persisted));
    assert(strcmp(settings[0], private_hex) == 0);
    assert(strcmp(settings[1], (char *)persisted.public_hex) == 0);
    assert(strcmp(settings[2], (char *)persisted.key_id) == 0);
    WipeDeviceKey(&persisted);
    assert(LoadOrCreateDeviceKey(&persisted));
    assert(strcmp(settings[0], private_hex) == 0);
    settings[2][0] = settings[2][0] == '0' ? '1' : '0';
    assert(!LoadOrCreateDeviceKey(&persisted));
    assert(settings[0][0] != 0);
    WipeDeviceKey(&generated);
    WipeDeviceKey(&loaded);
    WipeDeviceKey(&persisted);
    for (size_t index = 0; index < 64; ++index) {
        assert(generated.private_key[index] == 0);
        assert(loaded.private_key[index] == 0);
    }
    puts("Inbe Ziran Ed25519 device key passed");
    return 0;
}
