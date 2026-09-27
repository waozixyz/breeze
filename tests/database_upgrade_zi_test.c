#define _GNU_SOURCE
#include "sqlite3.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int32_t select_database_path(uint8_t *legacy, uint8_t *current,
    uint8_t *marker, uint8_t *temporary, uint8_t *database_name,
    uint8_t *output, uint64_t output_capacity);

static int deny_marker;
static int deny_rename;

int32_t path_exists(uint8_t *path)
{
    struct stat info;
    return path != NULL && stat((char *)path, &info) == 0;
}

int32_t storage_remove_path(uint8_t *path)
{
    return path != NULL && remove((char *)path) == 0;
}

int32_t storage_rename_path(uint8_t *source, uint8_t *destination)
{
    if(deny_rename || path_exists(destination))
        return 0;
    return rename((char *)source, (char *)destination) == 0;
}

int32_t storage_write_migration_marker(uint8_t *path, uint8_t *value)
{
    if(deny_marker)
        return 0;
    FILE *file = fopen((char *)path, "wb");
    if(file == NULL)
        return 0;
    int ok = fprintf(file, "%s\n", (char *)value) > 0 && fflush(file) == 0;
    if(fclose(file) != 0)
        ok = 0;
    return ok;
}

uint8_t *LoadFileData(uint8_t *path, int32_t *size)
{
    FILE *file = fopen((char *)path, "rb");
    if(file == NULL)
        return NULL;
    assert(fseek(file, 0, SEEK_END) == 0);
    long length = ftell(file);
    assert(length >= 0 && length < INT32_MAX);
    assert(fseek(file, 0, SEEK_SET) == 0);
    uint8_t *bytes = malloc((size_t)length + 1);
    assert(bytes != NULL);
    assert(fread(bytes, 1, (size_t)length, file) == (size_t)length);
    assert(fclose(file) == 0);
    *size = (int32_t)length;
    return bytes;
}

void UnloadFileData(uint8_t *bytes)
{
    free(bytes);
}

static void paths(const char *parent, const char *name, char *old,
                  char *current, char *marker, char *temporary)
{
    int count = snprintf(old, 512, "%s/%s-breathing.db", parent, name);
    assert(count > 0 && count < 512);
    count = snprintf(current, 512, "%s/%s-inbe.db", parent, name);
    assert(count > 0 && count < 512);
    count = snprintf(marker, 512, "%s.migrated", current);
    assert(count > 0 && count < 512);
    count = snprintf(temporary, 512, "%s.migrating", current);
    assert(count > 0 && count < 512);
}

static int select_path(char *old, char *current, char *marker,
                       char *temporary, char *output, size_t capacity)
{
    return select_database_path((uint8_t *)old, (uint8_t *)current,
        (uint8_t *)marker, (uint8_t *)temporary, (uint8_t *)"inbe.db",
        (uint8_t *)output, capacity);
}

static void open_database(const char *path, sqlite3 **database)
{
    assert(sqlite3_open(path, database) == SQLITE_OK);
}

static void execute(sqlite3 *database, const char *sql)
{
    char *error = NULL;
    int result = sqlite3_exec(database, sql, NULL, NULL, &error);
    if(result != SQLITE_OK)
        fprintf(stderr, "%s\n", error != NULL ? error : sql);
    assert(result == SQLITE_OK);
    sqlite3_free(error);
}

static long long scalar(const char *path)
{
    sqlite3 *database = NULL;
    sqlite3_stmt *statement = NULL;
    long long value;
    open_database(path, &database);
    assert(sqlite3_prepare_v2(database, "SELECT value FROM saved", -1,
                              &statement, NULL) == SQLITE_OK);
    assert(sqlite3_step(statement) == SQLITE_ROW);
    value = sqlite3_column_int64(statement, 0);
    assert(sqlite3_finalize(statement) == SQLITE_OK);
    assert(sqlite3_close(database) == SQLITE_OK);
    return value;
}

static void test_fresh(const char *parent)
{
    char old[512], current[512], marker[512], temporary[512], output[512];
    paths(parent, "fresh", old, current, marker, temporary);
    assert(select_path(old, current, marker, temporary, output,
                       sizeof output));
    assert(strcmp(output, current) == 0);
    assert(!path_exists((uint8_t *)current));
}

static void test_wal_copy(const char *parent)
{
    char old[512], current[512], marker[512], temporary[512], output[512];
    sqlite3 *database = NULL;
    paths(parent, "wal", old, current, marker, temporary);
    open_database(old, &database);
    execute(database, "PRAGMA journal_mode=WAL; CREATE TABLE saved(value INTEGER);"
                      "INSERT INTO saved VALUES(1234567);");
    assert(!select_path(old, current, marker, temporary, output, 4));
    assert(output[0] == '\0');
    assert(!path_exists((uint8_t *)current));
    assert(select_path(old, current, marker, temporary, output,
                       sizeof output));
    assert(strcmp(output, current) == 0);
    assert(path_exists((uint8_t *)marker));
    assert(!path_exists((uint8_t *)temporary));
    assert(scalar(current) == 1234567);
    assert(sqlite3_close(database) == SQLITE_OK);
    assert(scalar(old) == 1234567);
    assert(select_path(old, current, marker, temporary, output,
                       sizeof output));
    assert(strcmp(output, current) == 0);
    assert(unlink(marker) == 0);
    assert(unlink(current) == 0);
    assert(unlink(old) == 0);
}

static void test_conflict(const char *parent)
{
    char old[512], current[512], marker[512], temporary[512], output[512];
    sqlite3 *database = NULL;
    paths(parent, "conflict", old, current, marker, temporary);
    open_database(old, &database);
    execute(database, "CREATE TABLE saved(value INTEGER); INSERT INTO saved VALUES(1);");
    assert(sqlite3_close(database) == SQLITE_OK);
    open_database(current, &database);
    execute(database, "CREATE TABLE saved(value INTEGER); INSERT INTO saved VALUES(2);");
    assert(sqlite3_close(database) == SQLITE_OK);
    assert(!select_path(old, current, marker, temporary, output,
                        sizeof output));
    assert(output[0] == '\0');
    assert(scalar(old) == 1);
    assert(scalar(current) == 2);
    assert(storage_write_migration_marker((uint8_t *)marker,
        (uint8_t *)"wrong.db"));
    assert(!select_path(old, current, marker, temporary, output,
                        sizeof output));
    assert(output[0] == '\0');
    assert(storage_write_migration_marker((uint8_t *)marker,
        (uint8_t *)"inbe.db"));
    assert(select_path(old, current, marker, temporary, output,
                       sizeof output));
    assert(strcmp(output, current) == 0);
    assert(unlink(marker) == 0);
    assert(unlink(current) == 0);
    assert(unlink(old) == 0);
}

static void test_failed_copy(const char *parent)
{
    char old[512], current[512], marker[512], temporary[512], output[512];
    paths(parent, "bad", old, current, marker, temporary);
    FILE *file = fopen(old, "wb");
    assert(file != NULL);
    assert(fputs("invalid sqlite", file) >= 0);
    assert(fclose(file) == 0);
    assert(select_path(old, current, marker, temporary, output,
                       sizeof output));
    assert(strcmp(output, old) == 0);
    assert(!path_exists((uint8_t *)current));
    assert(!path_exists((uint8_t *)temporary));
    assert(unlink(old) == 0);
}

static void test_failed_publish(const char *parent)
{
    char old[512], current[512], marker[512], temporary[512], output[512];
    sqlite3 *database = NULL;
    paths(parent, "failure", old, current, marker, temporary);
    open_database(old, &database);
    execute(database, "CREATE TABLE saved(value INTEGER); INSERT INTO saved VALUES(9);");
    assert(sqlite3_close(database) == SQLITE_OK);
    deny_marker = 1;
    assert(!select_path(old, current, marker, temporary, output,
                        sizeof output));
    deny_marker = 0;
    assert(output[0] == '\0');
    assert(path_exists((uint8_t *)current));
    assert(scalar(current) == 9);
    assert(!path_exists((uint8_t *)temporary));
    assert(!select_path(old, current, marker, temporary, output,
                        sizeof output));
    assert(unlink(current) == 0);
    deny_rename = 1;
    assert(select_path(old, current, marker, temporary, output,
                       sizeof output));
    deny_rename = 0;
    assert(strcmp(output, old) == 0);
    assert(!path_exists((uint8_t *)current));
    assert(!path_exists((uint8_t *)temporary));
    assert(scalar(old) == 9);
    assert(!path_exists((uint8_t *)marker));
    assert(unlink(old) == 0);
}

int main(void)
{
    char parent[] = "/tmp/inbe-database-upgrade-XXXXXX";
    assert(mkdtemp(parent) != NULL);
    test_fresh(parent);
    test_wal_copy(parent);
    test_conflict(parent);
    test_failed_copy(parent);
    test_failed_publish(parent);
    assert(rmdir(parent) == 0);
    puts("Inbe Ziran database upgrade passed");
    return 0;
}
