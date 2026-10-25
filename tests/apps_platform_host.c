#include "zir_string.h"
#include "ziran_host.h"
#include "zir_stream.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned char *payload;
static size_t payload_size;
static unsigned char *full_payload;
static size_t full_payload_size;
extern int32_t CheckPlatformModules(void);

String ProbeRoot(void)
{
    return StringView((char *)payload, payload_size);
}

String ProbeFullRoot(void)
{
    return StringView((char *)full_payload, full_payload_size);
}

/* This loader probe has no publisher or persisted settings. Network-package
 * authentication always fails; bundled identity checks still execute. */
int crypto_ed25519_check(const uint8_t *signature, const uint8_t *public_key,
                        const uint8_t *message, size_t length)
{
    (void)signature;
    (void)public_key;
    (void)message;
    (void)length;
    return -1;
}

int32_t storage_get_setting_int(String key)
{
    (void)key;
    return 0;
}

void app_web_storage_flush(void) {}

static unsigned char *read_payload(const char *path, size_t *size)
{
    FILE *file = fopen(path, "rb");
    if(file == NULL) {
        return NULL;
    }
    if(fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }
    long length = ftell(file);
    if(length <= 0 || fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }
    unsigned char *bytes = malloc((size_t)length);
    if(bytes == NULL || fread(bytes, 1, (size_t)length, file) != (size_t)length) {
        free(bytes);
        fclose(file);
        return NULL;
    }
    fclose(file);
    *size = (size_t)length;
    return bytes;
}

void *asset_entry_at(size_t index)
{
    (void)index;
    return NULL;
}

size_t asset_entry_total(void)
{
    return 0;
}

FILE *__wrap_tmpfile(void)
{
    return NULL;
}

int main(int argc, char **argv)
{
    setbuf(stdout, NULL);
    if(argc != 3) {
        return 10;
    }
    payload = read_payload(argv[1], &payload_size);
    full_payload = read_payload(argv[2], &full_payload_size);
    if(payload == NULL || full_payload == NULL) {
        free(payload);
        free(full_payload);
        return 11;
    }
    FILE *memory = ZirReadMemory(payload, payload_size);
    printf("Root bytes=%zu; memory stream opened=%d\n", payload_size, memory != NULL);
    if(memory == NULL) {
        return 14;
    }
    unsigned char signature[4];
    size_t read = fread(signature, 1, sizeof(signature), memory);
    long start = ftell(memory);
    int seek_end = fseek(memory, 0, SEEK_END);
    long end = ftell(memory);
    int seek_start = fseek(memory, start, SEEK_SET);
    printf("Memory stream: read=%zu start=%ld seek_end=%d end=%ld seek_start=%d error=%d\n",
           read, start, seek_end, end, seek_start, ferror(memory));
    fclose(memory);
    if(read != sizeof(signature) || start != 4 || seek_end != 0 ||
       end != (long)payload_size || seek_start != 0) {
        return 15;
    }
    Bundle *root = BundleOpenBytes(payload, payload_size);
    if(root == NULL) {
        return 16;
    }
    BundleClose(root);
    int result = CheckPlatformModules();
    free(payload);
    free(full_payload);
    printf("Root/nested module target probe: size_t=%zu, result=%d, tmpfile denied\n",
           sizeof(size_t), result);
    return result;
}
