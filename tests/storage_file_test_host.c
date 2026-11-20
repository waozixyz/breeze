// Read the fixture files using the same buffer ownership as the native host.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

uint8_t *LoadFileData(uint8_t *path, int32_t *size)
{
    *size = 0;
    FILE *file = fopen((const char *)path, "rb");
    if (file == NULL) return NULL;
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }
    long length = ftell(file);
    if (length < 0 || length > INT32_MAX || fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }
    uint8_t *bytes = calloc((size_t)length + 1, 1);
    if (bytes == NULL || fread(bytes, 1, (size_t)length, file) != (size_t)length) {
        free(bytes);
        bytes = NULL;
    }
    fclose(file);
    if (bytes != NULL) *size = (int32_t)length;
    return bytes;
}
