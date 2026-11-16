/* Exercise the decoder objects linked into the actual application. */
#include "zir_string_types.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern unsigned char *ImagePreviewDecode(String, String, int32_t *, int32_t *,
                                         int32_t *, bool *);
extern void ImagePreviewRelease(unsigned char *);

int __wrap_main(int argc, char **argv) {
    if (argc < 2) return 1;
    for (int i = 1; i < argc; ++i) {
        FILE *file = fopen(argv[i], "rb");
        if (!file || fseek(file, 0, SEEK_END)) return 2;
        long length = ftell(file);
        if (length <= 0 || length > 268435456 || fseek(file, 0, SEEK_SET)) return 3;
        unsigned char *encoded = malloc((size_t)length);
        if (!encoded || fread(encoded, 1, (size_t)length, file) != (size_t)length) return 4;
        fclose(file);
        const char *extension = strrchr(argv[i], '.');
        if (!extension) return 5;
        int32_t width = 0, height = 0, channels = 0;
        bool upright = false;
        unsigned char *pixels = ImagePreviewDecode(
            StringView((const char *)encoded, (size_t)length),
            StringView(extension, strlen(extension)),
            &width, &height, &channels, &upright);
        printf("%s %s magic=", argv[i], extension);
        for (int byte = 0; byte < 12 && byte < length; ++byte) printf("%02x", encoded[byte]);
        printf(" decoded=%dx%d channels=%d\n", width, height, channels);
        free(encoded);
        if (!pixels || width <= 0 || height <= 0 || channels < 1 || channels > 4) return 6;
        ImagePreviewRelease(pixels);
    }
    return 0;
}
