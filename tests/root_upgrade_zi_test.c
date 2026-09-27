#define _GNU_SOURCE
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int32_t migrate_data_root(uint8_t *legacy, uint8_t *current,
                          uint8_t *archive_suffix, uint8_t *output,
                          uint64_t output_capacity);

static int deny_rename;

int32_t storage_directory_exists(uint8_t *path)
{
    struct stat info;
    return path != NULL && stat((char *)path, &info) == 0 &&
           S_ISDIR(info.st_mode);
}

int32_t path_exists(uint8_t *path)
{
    struct stat info;
    return path != NULL && stat((char *)path, &info) == 0;
}

int32_t storage_rename_path(uint8_t *source, uint8_t *destination)
{
    if(deny_rename)
        return 0;
    return rename((char *)source, (char *)destination) == 0;
}

static void make_path(char *output, size_t capacity, const char *root,
                      const char *name)
{
    int count = snprintf(output, capacity, "%s/%s", root, name);
    assert(count > 0 && (size_t)count < capacity);
}

static void make_archive(char *output, size_t capacity, const char *current,
                         int ordinal)
{
    int count = snprintf(output, capacity, "%s.before-breathing-migration-%d",
                         current, ordinal);
    assert(count > 0 && (size_t)count < capacity);
}

static void write_marker(const char *directory, const char *value)
{
    char path[512];
    make_path(path, sizeof path, directory, "marker");
    FILE *file = fopen(path, "wb");
    assert(file != NULL);
    assert(fputs(value, file) >= 0);
    assert(fclose(file) == 0);
}

static void check_marker(const char *directory, const char *expected)
{
    char path[512];
    char value[32];
    make_path(path, sizeof path, directory, "marker");
    FILE *file = fopen(path, "rb");
    assert(file != NULL);
    assert(fgets(value, sizeof value, file) != NULL);
    assert(strcmp(value, expected) == 0);
    assert(fclose(file) == 0);
}

static void remove_marked_directory(const char *directory)
{
    char path[512];
    make_path(path, sizeof path, directory, "marker");
    assert(unlink(path) == 0);
    assert(rmdir(directory) == 0);
}

static void test_fresh(const char *parent)
{
    char legacy[512], current[512], output[512];
    make_path(legacy, sizeof legacy, parent, "fresh-old");
    make_path(current, sizeof current, parent, "fresh-current");
    assert(migrate_data_root((uint8_t *)legacy, (uint8_t *)current,
        (uint8_t *)".before-breathing-migration-", (uint8_t *)output,
        sizeof output));
    assert(strcmp(output, current) == 0);
    assert(!storage_directory_exists((uint8_t *)current));
}

static void test_move(const char *parent)
{
    char legacy[512], current[512], output[512];
    char too_small[4];
    make_path(legacy, sizeof legacy, parent, "move-old");
    make_path(current, sizeof current, parent, "move-current");
    assert(mkdir(legacy, 0700) == 0);
    write_marker(legacy, "old");
    assert(!migrate_data_root((uint8_t *)legacy, (uint8_t *)current,
        (uint8_t *)".before-breathing-migration-", (uint8_t *)too_small,
        sizeof too_small));
    assert(too_small[0] == '\0');
    check_marker(legacy, "old");
    assert(migrate_data_root((uint8_t *)legacy, (uint8_t *)current,
        (uint8_t *)".before-breathing-migration-", (uint8_t *)output,
        sizeof output));
    assert(strcmp(output, current) == 0);
    assert(!storage_directory_exists((uint8_t *)legacy));
    check_marker(current, "old");
    remove_marked_directory(current);
}

static void test_conflict(const char *parent)
{
    char legacy[512], current[512], archive1[512], archive2[512], output[512];
    make_path(legacy, sizeof legacy, parent, "conflict-old");
    make_path(current, sizeof current, parent, "conflict-current");
    make_archive(archive1, sizeof archive1, current, 1);
    make_archive(archive2, sizeof archive2, current, 2);
    assert(mkdir(legacy, 0700) == 0);
    assert(mkdir(current, 0700) == 0);
    assert(mkdir(archive1, 0700) == 0);
    write_marker(legacy, "old");
    write_marker(current, "new");
    write_marker(archive1, "prior");
    assert(migrate_data_root((uint8_t *)legacy, (uint8_t *)current,
        (uint8_t *)".before-breathing-migration-", (uint8_t *)output,
        sizeof output));
    assert(strcmp(output, current) == 0);
    check_marker(current, "old");
    check_marker(archive1, "prior");
    check_marker(archive2, "new");
    remove_marked_directory(current);
    remove_marked_directory(archive1);
    remove_marked_directory(archive2);
}

static void test_failed_move(const char *parent)
{
    char legacy[512], current[512], output[512];
    make_path(legacy, sizeof legacy, parent, "failed-old");
    make_path(current, sizeof current, parent, "failed-current");
    assert(mkdir(legacy, 0700) == 0);
    write_marker(legacy, "old");
    deny_rename = 1;
    assert(migrate_data_root((uint8_t *)legacy, (uint8_t *)current,
        (uint8_t *)".before-breathing-migration-", (uint8_t *)output,
        sizeof output));
    deny_rename = 0;
    assert(strcmp(output, legacy) == 0);
    check_marker(legacy, "old");
    remove_marked_directory(legacy);
}

static void test_failed_archive(const char *parent)
{
    char legacy[512], current[512], output[512];
    make_path(legacy, sizeof legacy, parent, "archive-failed-old");
    make_path(current, sizeof current, parent, "archive-failed-current");
    assert(mkdir(legacy, 0700) == 0);
    assert(mkdir(current, 0700) == 0);
    write_marker(legacy, "old");
    write_marker(current, "new");
    deny_rename = 1;
    assert(migrate_data_root((uint8_t *)legacy, (uint8_t *)current,
        (uint8_t *)".before-breathing-migration-", (uint8_t *)output,
        sizeof output));
    deny_rename = 0;
    assert(strcmp(output, legacy) == 0);
    check_marker(legacy, "old");
    check_marker(current, "new");
    remove_marked_directory(legacy);
    remove_marked_directory(current);
}

int main(void)
{
    char parent[] = "/tmp/inbe-root-upgrade-XXXXXX";
    assert(mkdtemp(parent) != NULL);
    test_fresh(parent);
    test_move(parent);
    test_conflict(parent);
    test_failed_move(parent);
    test_failed_archive(parent);
    assert(rmdir(parent) == 0);
    puts("Inbe Ziran data root upgrade passed");
    return 0;
}
