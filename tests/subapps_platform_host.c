#include "zir_string.h"
#include "ziran_host.h"
#include "zir_stream.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned char *payload;
static size_t payload_size;
extern int32_t CheckPlatformModules(void);

String ProbeRoot(void)
{
    return StringView((char *)payload, payload_size);
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
    if(argc != 2) {
        return 10;
    }
    FILE *file = fopen(argv[1], "rb");
    if(file == NULL || fseek(file, 0, SEEK_END) != 0) {
        return 11;
    }
    long length = ftell(file);
    if(length <= 0 || fseek(file, 0, SEEK_SET) != 0) {
        return 12;
    }
    payload_size = (size_t)length;
    payload = malloc(payload_size);
    if(payload == NULL || fread(payload, 1, payload_size, file) != payload_size) {
        return 13;
    }
    fclose(file);
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
    printf("Root/nested module target probe: size_t=%zu, result=%d, tmpfile denied\n",
           sizeof(size_t), result);
    return result;
}
