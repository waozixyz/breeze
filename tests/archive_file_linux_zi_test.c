#define _GNU_SOURCE
#include "storage/archive_file_linux.h"

#include <assert.h>
#include <sqlite3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int imported_databases;
static int inspected_databases;
static int imported_sessions;

static void write_file(const char *path, const void *data, size_t size)
{
    FILE *file = fopen(path, "wb");
    assert(file != NULL);
    assert(fwrite(data, 1, size, file) == size);
    assert(fclose(file) == 0);
}

static void read_file(const char *path, char *output, size_t size)
{
    FILE *file = fopen(path, "rb");
    assert(file != NULL);
    assert(fread(output, 1, size, file) == size);
    assert(fclose(file) == 0);
}

int32_t import_sqlite_db_file(String path, int32_t mode)
{
    char data[26] = {0};
    assert(mode == 0 || mode == 1);
    FILE *file = fopen(path.data, "rb");
    assert(file != NULL);
    assert(fread(data, 1, 10, file) == 10);
    if(memcmp(data, "SQLite for", 10) == 0) {
        assert(fread(data + 10, 1, 16, file) == 16);
        assert(memcmp(data, "SQLite format 3\0db-payload", 26) == 0);
    } else {
        assert(memcmp(data, "db-payload", 10) == 0);
    }
    assert(fclose(file) == 0);
    imported_databases++;
    return 1;
}

int32_t inspect_sqlite_db_file(String path, ArchiveInfo *info)
{
    char data[26] = {0};
    FILE *file = fopen(path.data, "rb");
    assert(file != NULL);
    assert(fread(data, 1, 10, file) == 10);
    if(memcmp(data, "SQLite for", 10) == 0) {
        assert(fread(data + 10, 1, 16, file) == 16);
        assert(memcmp(data, "SQLite format 3\0db-payload", 26) == 0);
    } else {
        assert(memcmp(data, "db-payload", 10) == 0);
    }
    assert(fclose(file) == 0);
    inspected_databases++;
    info->valid = 1;
    info->has_sessions = 1;
    info->session_count = 7;
    return 1;
}

int64_t storage_local_timestamp(int32_t year, int32_t month, int32_t day,
                                int32_t hour, int32_t minute, int32_t second)
{
    assert(year == 2026 && month == 6 && day == 13);
    assert(hour == 1 && minute == 2 && second == 3);
    return 1781312523;
}

int32_t storage_insert_legacy_session(int64_t timestamp, int32_t local_date,
                                      int32_t *rounds, int32_t count)
{
    assert(timestamp > 0 && local_date == 20260613);
    assert(count == 2 && rounds[0] == 31 && rounds[1] == 35);
    imported_sessions++;
    return 1;
}

static uint8_t *make_zip(const char *name, const char *content, size_t *size)
{
    size_t name_size = strlen(name);
    size_t data_size = strlen(content);
    size_t input_size = name_size + data_size;
    uint8_t *input = malloc(input_size);
    assert(input != NULL);
    memcpy(input, name, name_size);
    memcpy(input + name_size, content, data_size);
    ZipWriteItem item = {0, name_size, name_size, data_size};
    Slice input_view = {input, (int64_t)input_size};
    Slice items = {&item, 1};
    *size = (size_t)StoredZipSize(input_view, items);
    assert(*size > 0);
    uint8_t *zip = malloc(*size);
    assert(zip != NULL);
    assert(WriteStoredZip((Slice){zip, (int64_t)*size}, input_view, items) == *size);
    free(input);
    return zip;
}

int main(void)
{
    char root[] = "/tmp/inbe-archive-file-XXXXXX";
    assert(mkdtemp(root) != NULL);
    StorageState *state = storage_state_handle();
    snprintf((char *)state->root, sizeof state->root, "%s", root);
    char path[600], sentinel[600], occupied[600], text[11] = {0};
    snprintf(path, sizeof path, "%s/backup.zip", root);
    snprintf(sentinel, sizeof sentinel, "%s/import-inbe.db", root);
    snprintf(occupied, sizeof occupied, "%s/import-inbe.db.tmp1", root);
    write_file(sentinel, "sentinel", 8);
    write_file(occupied, "occupied", 8);

    size_t size;
    uint8_t *zip = make_zip("inbe-data/inbe.db", "db-payload", &size);
    write_file(path, zip, size);
    ArchiveInfo info = {0};
    assert(ArchiveInspectFile(StringView(path, strlen(path)), &info) == 1);
    assert(info.valid && info.session_count == 7 && inspected_databases == 1);
    assert(ArchiveImportFile(StringView(path, strlen(path)), 0) == 1);
    assert(imported_databases == 1);
    read_file(sentinel, text, 8);
    assert(memcmp(text, "sentinel", 8) == 0);
    read_file(occupied, text, 8);
    assert(memcmp(text, "occupied", 8) == 0);

    ZipEntry entry = FindZipEntry((Slice){zip, (int64_t)size},
                                  StringView("inbe-data/inbe.db", 17));
    assert(entry.found);
    zip[entry.data_start] ^= 1;
    write_file(path, zip, size);
    assert(ArchiveImportFile(StringView(path, strlen(path)), 0) == 0);
    assert(imported_databases == 1);
    free(zip);

    zip = make_zip("breathing-data/breathing.db", "db-payload", &size);
    write_file(path, zip, size);
    assert(ArchiveInspectFile(StringView(path, strlen(path)), &info) == 1);
    assert(ArchiveImportFile(StringView(path, strlen(path)), 0) == 1);
    assert(inspected_databases == 2 && imported_databases == 2);
    free(zip);

    zip = make_zip("breathing-data/sessions/2026/06/13/breathing-010203",
                   "31\n35\n", &size);
    write_file(path, zip, size);
    info = (ArchiveInfo){0};
    assert(ArchiveInspectFile(StringView(path, strlen(path)), &info) == 1);
    assert(info.valid && info.has_sessions && info.session_count == 1);
    assert(imported_sessions == 0);
    assert(ArchiveImportFile(StringView(path, strlen(path)), 0) == 1);
    assert(imported_sessions == 1);
    free(zip);

    write_file(path, "invalid", 7);
    assert(ArchiveInspectFile(StringView(path, strlen(path)), &info) == 0);
    assert(ArchiveImportFile(StringView(path, strlen(path)), 1) == 0);
    assert(inspected_databases == 2 && imported_databases == 2);

    write_file(path, "SQLite format 3\0db-payload", 26);
    assert(ArchiveInspectFile(StringView(path, strlen(path)), &info) == 1);
    assert(ArchiveImportFile(StringView(path, strlen(path)), 1) == 1);
    assert(inspected_databases == 3 && imported_databases == 3);

    char source_path[600], export_path[600], snapshot_occupied[600];
    char output_occupied[600], restored_path[600];
    snprintf(source_path, sizeof source_path, "%s/source.db", root);
    snprintf(export_path, sizeof export_path, "%s/export.zip", root);
    snprintf(snapshot_occupied, sizeof snapshot_occupied,
             "%s/export-inbe.db.tmp1", root);
    snprintf(output_occupied, sizeof output_occupied, "%s/export.zip.tmp1", root);
    snprintf(restored_path, sizeof restored_path, "%s/restored.db", root);
    write_file(snapshot_occupied, "snapshot-sentinel", 17);
    write_file(output_occupied, "output-sentinel", 15);
    sqlite3 *source = NULL;
    assert(sqlite3_open(source_path, &source) == SQLITE_OK);
    assert(sqlite3_exec(source, "PRAGMA journal_mode=WAL;"
                              "CREATE TABLE sessions(id TEXT,deleted_at INT);"
                              "CREATE TABLE habits(id TEXT,deleted_at INT);"
                              "INSERT INTO sessions VALUES('one',0);"
                              "INSERT INTO habits VALUES('two',0);",
                        NULL, NULL, NULL) == SQLITE_OK);
    state->db = source;
    strcpy((char *)state->user_id, "user-\"\\");
    assert(ArchiveExportFile(StringView(export_path, strlen(export_path))) == 1);
    struct stat export_stat;
    assert(stat(export_path, &export_stat) == 0);
    assert(export_stat.st_size > 0);
    assert(ArchiveExportFile(StringView(export_path, strlen(export_path))) == 0);
    struct stat after_stat;
    assert(stat(export_path, &after_stat) == 0);
    assert(after_stat.st_size == export_stat.st_size);
    read_file(snapshot_occupied, text, 10);
    assert(memcmp(text, "snapshot-s", 10) == 0);
    read_file(output_occupied, text, 10);
    assert(memcmp(text, "output-sen", 10) == 0);

    uint8_t *export_bytes = malloc((size_t)export_stat.st_size);
    assert(export_bytes != NULL);
    read_file(export_path, (char *)export_bytes, (size_t)export_stat.st_size);
    Slice export_view = {export_bytes, export_stat.st_size};
    ZipEntry metadata_entry = FindZipEntry(export_view,
        StringView("inbe-data/metadata.json", strlen("inbe-data/metadata.json")));
    ZipEntry database_entry = FindZipEntry(export_view,
        StringView("inbe-data/inbe.db", strlen("inbe-data/inbe.db")));
    assert(metadata_entry.found && metadata_entry.size < 512);
    assert(database_entry.found && database_entry.size > 100);
    char metadata[512] = {0};
    assert(CopyStoredZipEntry(export_view, metadata_entry,
                              (Slice){metadata, (int64_t)metadata_entry.size}));
    assert(strstr(metadata, "\"format\":\"inbe-data-sqlite\"") != NULL);
    assert(strstr(metadata, "\"app_version\":\"2.0.6\"") != NULL);
    assert(strstr(metadata, "\"user_id\":\"user-\\\"\\\\\"") != NULL);
    assert(strstr(metadata, "\"session_count\":1") != NULL);
    assert(strstr(metadata, "\"habit_count\":1") != NULL);
    uint8_t *restored_bytes = malloc((size_t)database_entry.size);
    assert(restored_bytes != NULL);
    assert(CopyStoredZipEntry(export_view, database_entry,
                              (Slice){restored_bytes, (int64_t)database_entry.size}));
    assert(memcmp(restored_bytes, "SQLite format 3", 15) == 0);
    write_file(restored_path, restored_bytes, (size_t)database_entry.size);
    sqlite3 *restored = NULL;
    assert(sqlite3_open_v2(restored_path, &restored, SQLITE_OPEN_READONLY, NULL) == SQLITE_OK);
    sqlite3_stmt *row = NULL;
    assert(sqlite3_prepare_v2(restored,
        "SELECT (SELECT COUNT(*) FROM sessions)+(SELECT COUNT(*) FROM habits)",
        -1, &row, NULL) == SQLITE_OK);
    assert(sqlite3_step(row) == SQLITE_ROW);
    assert(sqlite3_column_int(row, 0) == 2);
    assert(sqlite3_finalize(row) == SQLITE_OK);
    assert(sqlite3_close(restored) == SQLITE_OK);
    free(restored_bytes);
    free(export_bytes);
    state->db = NULL;
    assert(sqlite3_close(source) == SQLITE_OK);

    assert(unlink(path) == 0);
    assert(unlink(export_path) == 0);
    assert(unlink(source_path) == 0);
    assert(unlink(restored_path) == 0);
    assert(unlink(snapshot_occupied) == 0);
    assert(unlink(output_occupied) == 0);
    assert(unlink(sentinel) == 0);
    assert(unlink(occupied) == 0);
    assert(rmdir(root) == 0);
    puts("Inbe Ziran archive file import and inspection passed");
    return 0;
}
