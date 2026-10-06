#include "assets_link_behavior.h"
#include "assets_host.h"

#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

int
main(int argc, char **argv)
{
    assert(argc == 2);
    AssetBlob style = asset_lookup((uint8_t *)"assets/styles/inbe.kss");
    AssetBlob missing = asset_lookup((uint8_t *)"assets/styles/missing.kss");

    assert(style.found && style.size > 4);
    /* Verify the complete payload, including declarations before selectors. */
    FILE *file = fopen(argv[1], "rb");
    assert(file != NULL && fseek(file, 0, SEEK_END) == 0);
    long size = ftell(file);
    assert(size > 0 && (size_t)size == style.size && fseek(file, 0, SEEK_SET) == 0);
    unsigned char *expected = malloc((size_t)size);
    assert(expected != NULL && fread(expected, 1, (size_t)size, file) == (size_t)size);
    fclose(file);
    assert(memcmp(style.data, expected, style.size) == 0);
    free(expected);
    assert(strcmp((const char *)style.mime, "text/plain") == 0);
    assert(!missing.found);
    assert(Answer() == 42);
    return 0;
}
