#define _POSIX_C_SOURCE 200809L
#include "zir_string.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int32_t path_exists(uint8_t *path);
int32_t storage_directory_exists(uint8_t *path);
int32_t storage_rename_path(uint8_t *source, uint8_t *destination);
int32_t storage_remove_path(uint8_t *path);
int32_t storage_write_migration_marker(uint8_t *path, uint8_t *name);
int32_t storage_ensure_dir(String path);

static void
join(char *output, size_t capacity, const char *root, const char *name)
{
    int result = snprintf(output, capacity, "%s/%s", root, name);
    assert(result > 0 && (size_t)result < capacity);
}

int
main(void)
{
    char root[] = "/tmp/inbe-paths-XXXXXX";
    assert(mkdtemp(root) != NULL);
    char nested[256], child[256], marker[256], other[256];
    join(nested, sizeof nested, root, "private");
    join(child, sizeof child, nested, "child");
    join(marker, sizeof marker, root, "inbe.db.migrated");
    join(other, sizeof other, root, "existing");

    assert(storage_ensure_dir(StringView(child, strlen(child))) == 1);
    assert(storage_directory_exists((uint8_t *)child) == 1);
    struct stat info;
    assert(stat(nested, &info) == 0 && (info.st_mode & 0777) == 0700);
    assert(stat(child, &info) == 0 && (info.st_mode & 0777) == 0700);
    assert(storage_ensure_dir(StringView(child, strlen(child))) == 1);

    uint8_t name[] = "inbe.db";
    assert(storage_write_migration_marker((uint8_t *)marker, name) == 1);
    assert(path_exists((uint8_t *)marker) == 1);
    assert(storage_directory_exists((uint8_t *)marker) == 0);
    FILE *file = fopen(marker, "rb");
    assert(file != NULL);
    char contents[32] = {0};
    assert(fread(contents, 1, sizeof contents, file) == 8);
    assert(memcmp(contents, "inbe.db\n", 8) == 0);
    assert(fclose(file) == 0);

    file = fopen(other, "wb");
    assert(file != NULL && fputs("keep", file) >= 0 && fclose(file) == 0);
    assert(storage_rename_path((uint8_t *)marker, (uint8_t *)other) == 0);
    file = fopen(other, "rb");
    assert(file != NULL);
    memset(contents, 0, sizeof contents);
    assert(fread(contents, 1, sizeof contents, file) == 4);
    assert(memcmp(contents, "keep", 4) == 0);
    assert(fclose(file) == 0);
    assert(storage_remove_path((uint8_t *)other) == 1);
    assert(storage_rename_path((uint8_t *)marker, (uint8_t *)other) == 1);
    assert(path_exists((uint8_t *)marker) == 0);
    assert(storage_remove_path((uint8_t *)other) == 1);

    assert(rmdir(child) == 0);
    assert(rmdir(nested) == 0);
    assert(rmdir(root) == 0);
    puts("Ziran storage paths preserve private directories and migration markers");
    return 0;
}
