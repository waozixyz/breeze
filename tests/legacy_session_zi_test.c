#define _GNU_SOURCE
#include "storage/legacy_session.h"
#include "storage/legacy_session_files.h"
#include "storage/legacy_session_time.h"
#include "storage/legacy_session_zip.h"
#include <assert.h>
#include <fts.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

const char *zlibVersion(void);

/* The generated Ziran zlib boundary uses the same native stream ABI. */
extern int deflateInit2_(ZStream *, int, int, int, int, int,
                         const char *, int);
extern int deflate(ZStream *, int);
extern int deflateEnd(ZStream *);

static int insert_calls;
static int insert_result = 1;
static int last_local_date;
static int last_rounds[LegacyMaxRounds];
static int last_round_count;
static int migration_marked;
static int persist_calls;

LegacyPaths LoadDirectoryFilesEx(uint8_t *root, uint8_t *filter,
                                 bool recursive)
{
    (void)filter;
    assert(recursive);
    LegacyPaths result = {0};
    char *roots[] = {(char *)root, NULL};
    FTS *tree = fts_open(roots, FTS_PHYSICAL | FTS_NOCHDIR, NULL);
    assert(tree != NULL);
    FTSENT *entry;
    while((entry = fts_read(tree)) != NULL) {
        if(entry->fts_level == 0 || entry->fts_info == FTS_DP)
            continue;
        uint8_t **next = realloc(result.paths,
            (result.count + 1) * sizeof(*result.paths));
        assert(next != NULL);
        result.paths = next;
        result.paths[result.count] = (uint8_t *)strdup(entry->fts_path);
        assert(result.paths[result.count] != NULL);
        result.count++;
    }
    assert(fts_close(tree) == 0);
    return result;
}

void UnloadDirectoryFiles(LegacyPaths paths)
{
    for(uint32_t index = 0; index < paths.count; index++)
        free(paths.paths[index]);
    free(paths.paths);
}

bool IsPathFile(uint8_t *path)
{
    struct stat info;
    return stat((char *)path, &info) == 0 && S_ISREG(info.st_mode);
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

int32_t meta_equals(uint8_t *key, uint8_t *value)
{
    assert(strcmp((char *)key, "legacy_file_sessions_migrated") == 0);
    assert(strcmp((char *)value, "1") == 0);
    return migration_marked;
}

int32_t db_exec_text(uint8_t *sql, uint8_t *value)
{
    assert(strstr((char *)sql, "legacy_file_sessions_migrated") != NULL);
    assert(strcmp((char *)value, "1") == 0);
    migration_marked = 1;
    return 1;
}

void storage_schedule_persist(void)
{
    persist_calls++;
}

int32_t storage_insert_legacy_session(int64_t started_at, int32_t local_date,
                                      int32_t *rounds, int32_t round_count)
{
    assert(started_at > 0);
    insert_calls++;
    last_local_date = local_date;
    last_round_count = round_count;
    memcpy(last_rounds, rounds, (size_t)round_count * sizeof(int));
    return insert_result;
}

static void test_paths(void)
{
    LegacySessionDate date = {0};
    assert(LegacyParsePath((uint8_t *)
        "sessions/2024/02/29/breathing-010203", &date));
    assert(date.year == 2024 && date.month == 2 && date.day == 29);
    assert(date.hour == 1 && date.minute == 2 && date.second == 3);
    assert(LegacyIsSessionPath((uint8_t *)
        "sessions/2024/02/29/breathing-010203"));
    assert(LegacyParsePath((uint8_t *)
        "/home/inbe/2026/06/13/breathing-235959.txt", &date));
    assert(date.year == 2026 && date.month == 6 && date.day == 13);
    assert(date.hour == 23 && date.minute == 59 && date.second == 59);
    assert(!LegacyParsePath((uint8_t *)
        "2026/02/29/breathing-010203", &date));
    assert(!LegacyParsePath((uint8_t *)
        "2026/06/13/breathing-240000", &date));
    assert(!LegacyParsePath((uint8_t *)
        "2026/06/13/breathing-010203extra", &date));
    assert(!LegacyParsePath((uint8_t *)
        "2026/06/13/other-010203", &date));
}

static void test_local_timestamp(void)
{
    struct tm date = {0};
    date.tm_year = 2026 - 1900;
    date.tm_mon = 6 - 1;
    date.tm_mday = 13;
    date.tm_hour = 1;
    date.tm_min = 2;
    date.tm_sec = 3;
    date.tm_isdst = -1;
    assert(storage_local_timestamp(2026, 6, 13, 1, 2, 3) ==
           (int64_t)mktime(&date));
    date.tm_year = 2400 - 1900;
    date.tm_mon = 2 - 1;
    date.tm_mday = 29;
    date.tm_hour = 23;
    date.tm_min = 59;
    date.tm_sec = 59;
    date.tm_isdst = -1;
    assert(storage_local_timestamp(2400, 2, 29, 23, 59, 59) ==
           (int64_t)mktime(&date));
}

static void test_rounds_and_import(void)
{
    static const char bytes[] = " 45 \n0\n\t60\r\njunk\n2147483648\n75\r\n";
    int32_t rounds[LegacyMaxRounds] = {0};
    assert(LegacyParseRounds((uint8_t *)bytes, sizeof bytes - 1,
                             rounds, LegacyMaxRounds) == 3);
    assert(rounds[0] == 45 && rounds[1] == 60 && rounds[2] == 75);
    assert(LegacyParseRounds((uint8_t *)bytes, sizeof bytes - 1,
                             rounds, 2) == 2);
    assert(LegacyImportBytes((uint8_t *)
        "sessions/2026/06/13/breathing-010203", (uint8_t *)bytes,
        sizeof bytes - 1));
    assert(insert_calls == 1);
    assert(last_local_date == 20260613);
    assert(last_round_count == 3);
    assert(last_rounds[0] == 45 && last_rounds[1] == 60 &&
           last_rounds[2] == 75);
    assert(!LegacyImportBytes((uint8_t *)
        "sessions/2026/06/13/other-010203", (uint8_t *)bytes,
        sizeof bytes - 1));
    assert(insert_calls == 1);
    insert_result = 0;
    assert(!LegacyImportBytes((uint8_t *)
        "sessions/2026/06/13/breathing-010203", (uint8_t *)bytes,
        sizeof bytes - 1));
    assert(insert_calls == 2);
}

static void write_text(const char *path, const char *text)
{
    FILE *file = fopen(path, "wb");
    assert(file != NULL);
    assert(fputs(text, file) >= 0);
    assert(fclose(file) == 0);
}

static void test_startup_scan(void)
{
    char root[] = "/tmp/inbe-legacy-session-XXXXXX";
    char year[512], month[512], day[512], valid[512], invalid[512];
    assert(mkdtemp(root) != NULL);
    assert(snprintf(year, sizeof year, "%s/2026", root) < (int)sizeof year);
    assert(snprintf(month, sizeof month, "%s/06", year) < (int)sizeof month);
    assert(snprintf(day, sizeof day, "%s/13", month) < (int)sizeof day);
    assert(snprintf(valid, sizeof valid, "%s/breathing-010203", day) <
           (int)sizeof valid);
    assert(snprintf(invalid, sizeof invalid, "%s/breathing-020304", day) <
           (int)sizeof invalid);
    assert(mkdir(year, 0700) == 0);
    assert(mkdir(month, 0700) == 0);
    assert(mkdir(day, 0700) == 0);
    write_text(valid, "31\n35\n");
    write_text(invalid, "empty\n");
    insert_calls = 0;
    migration_marked = 0;
    persist_calls = 0;
    insert_result = 1;
    assert(!migrate_legacy_file_sessions_once((uint8_t *)root));
    assert(insert_calls == 1);
    assert(!migration_marked);
    write_text(invalid, "39\n27\n");
    assert(migrate_legacy_file_sessions_once((uint8_t *)root));
    assert(insert_calls == 3);
    assert(migration_marked && persist_calls == 1);
    assert(migrate_legacy_file_sessions_once((uint8_t *)root));
    assert(insert_calls == 3);
    assert(access(valid, F_OK) == 0 && access(invalid, F_OK) == 0);
    assert(unlink(valid) == 0 && unlink(invalid) == 0);
    assert(rmdir(day) == 0 && rmdir(month) == 0 && rmdir(year) == 0);
    assert(rmdir(root) == 0);
}

static void test_zip_session_import(void)
{
    const char *metadata_name = "metadata.json";
    const char *session_name =
        "custom-root/sessions/2026/06/13/breathing-010203";
    const char *metadata = "{}";
    const char *session = "31\n35\n";
    uint8_t input[256] = {0};
    size_t cursor = 0;
    ZipWriteItem items[2] = {0};
    const char *names[] = {metadata_name, session_name};
    const char *contents[] = {metadata, session};
    for(size_t i = 0; i < 2; i++) {
        items[i].name_start = cursor;
        items[i].name_size = strlen(names[i]);
        memcpy(input + cursor, names[i], items[i].name_size);
        cursor += items[i].name_size;
        items[i].data_start = cursor;
        items[i].data_size = strlen(contents[i]);
        memcpy(input + cursor, contents[i], items[i].data_size);
        cursor += items[i].data_size;
    }
    Slice source = {input, (int64_t)cursor};
    Slice entries = {items, 2};
    uint64_t size = StoredZipSize(source, entries);
    assert(size > 0);
    uint8_t *archive = malloc((size_t)size);
    assert(archive != NULL);
    Slice bytes = {archive, (int64_t)size};
    assert(WriteStoredZip(bytes, source, entries) == size);
    insert_calls = 0;
    insert_result = 1;
    assert(LegacyCountZipSessions(bytes) == 1);
    assert(insert_calls == 0);
    assert(LegacyImportZipSessions(bytes) == 1);
    assert(insert_calls == 1 && last_local_date == 20260613);
    assert(last_round_count == 2 && last_rounds[0] == 31 &&
           last_rounds[1] == 35);
    ZipEntry entry = FindZipEntry(bytes,
        StringView(session_name, strlen(session_name)));
    assert(entry.found);
    archive[entry.data_start] ^= 1;
    assert(LegacyCountZipSessions(bytes) == -1);
    assert(LegacyImportZipSessions(bytes) == -1);
    assert(insert_calls == 1);
    archive[entry.data_start] ^= 1;
    insert_result = 0;
    assert(LegacyImportZipSessions(bytes) == -1);
    assert(insert_calls == 2);
    free(archive);
}

static void put_u16(uint8_t *bytes, size_t at, unsigned value)
{
    bytes[at] = (uint8_t)value;
    bytes[at + 1] = (uint8_t)(value >> 8);
}

static void put_u32(uint8_t *bytes, size_t at, uint32_t value)
{
    put_u16(bytes, at, value);
    put_u16(bytes, at + 2, value >> 16);
}

static void test_deflated_zip_session_import(void)
{
    const char *name =
        "breathing-data/sessions/2026/06/13/breathing-020304";
    const char *contents = "39\n27\n";
    size_t name_size = strlen(name);
    size_t contents_size = strlen(contents);
    uint8_t compressed[128] = {0};
    ZStream stream = {0};
    assert(deflateInit2_(&stream, -1, 8, -15, 8, 0,
                         (const char *)zlibVersion(), sizeof stream) == 0);
    stream.next_in = (uint8_t *)contents;
    stream.avail_in = (uint32_t)contents_size;
    stream.next_out = compressed;
    stream.avail_out = sizeof compressed;
    assert(deflate(&stream, 4) == 1);
    size_t compressed_size = stream.total_out;
    assert(deflateEnd(&stream) == 0);

    size_t central = 30 + name_size + compressed_size;
    size_t end = central + 46 + name_size;
    size_t size = end + 22;
    uint8_t *archive = calloc(size, 1);
    assert(archive != NULL);
    uint32_t checksum = ZipCRC32((Slice){(void *)contents,
                                       (int64_t)contents_size});
    put_u32(archive, 0, 0x04034b50);
    put_u16(archive, 4, 20);
    put_u16(archive, 8, 8);
    put_u32(archive, 14, checksum);
    put_u32(archive, 18, (uint32_t)compressed_size);
    put_u32(archive, 22, (uint32_t)contents_size);
    put_u16(archive, 26, (unsigned)name_size);
    memcpy(archive + 30, name, name_size);
    memcpy(archive + 30 + name_size, compressed, compressed_size);
    put_u32(archive, central, 0x02014b50);
    put_u16(archive, central + 4, 20);
    put_u16(archive, central + 6, 20);
    put_u16(archive, central + 10, 8);
    put_u32(archive, central + 16, checksum);
    put_u32(archive, central + 20, (uint32_t)compressed_size);
    put_u32(archive, central + 24, (uint32_t)contents_size);
    put_u16(archive, central + 28, (unsigned)name_size);
    memcpy(archive + central + 46, name, name_size);
    put_u32(archive, end, 0x06054b50);
    put_u16(archive, end + 8, 1);
    put_u16(archive, end + 10, 1);
    put_u32(archive, end + 12, (uint32_t)(46 + name_size));
    put_u32(archive, end + 16, (uint32_t)central);
    insert_result = 1;
    insert_calls = 0;
    assert(LegacyCountZipSessions((Slice){archive, (int64_t)size}) == 1);
    assert(insert_calls == 0);
    assert(LegacyImportZipSessions((Slice){archive, (int64_t)size}) == 1);
    assert(insert_calls == 1 && last_local_date == 20260613);
    assert(last_round_count == 2 && last_rounds[0] == 39 &&
           last_rounds[1] == 27);
    free(archive);
}

int main(void)
{
    assert(setenv("TZ", "UTC", 1) == 0);
    tzset();
    test_paths();
    test_local_timestamp();
    test_rounds_and_import();
    test_startup_scan();
    test_zip_session_import();
    test_deflated_zip_session_import();
    puts("Inbe Ziran historical session parser and import passed");
    return 0;
}
