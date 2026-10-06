#include "zir_string.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static const char *fixtures;
static void *allocated[64];
static int count;

String PackageFixture(String name)
{
    char path[4096];
    assert(count < 64);
    assert(snprintf(path, sizeof(path), "%s/%.*s", fixtures, (int)name.length, name.data) > 0);
    FILE *file = fopen(path, "rb");
    assert(file && fseek(file, 0, SEEK_END) == 0);
    long length = ftell(file);
    assert(length > 0 && fseek(file, 0, SEEK_SET) == 0);
    char *data = malloc((size_t)length);
    assert(data && fread(data, 1, (size_t)length, file) == (size_t)length);
    fclose(file);
    allocated[count++] = data;
    return StringView(data, (size_t)length);
}

extern int32_t CheckPackageReleases(void);
int main(int argc, char **argv)
{
    assert(argc == 2);
    fixtures = argv[1];
    int result = CheckPackageReleases();
    for(int i = 0; i < count; i++) free(allocated[i]);
    if(result) fprintf(stderr, "Package release check failed: %d\n", result);
    return result != 0;
}
