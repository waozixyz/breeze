#include "zir_string.h"
#include "practice_downloads_behavior.h"
#include "assets.h"
#include "file_download.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdatomic.h>
#include <time.h>

void FixtureContentYield(void) { usleep(1000); }
static atomic_int content_blocked;
static atomic_int content_entered;

void FixtureBlockContent(bool blocked)
{
    atomic_store(&content_entered, 0);
    atomic_store(&content_blocked, blocked);
}

bool FixtureContentStarted(void) { return atomic_load(&content_entered) != 0; }

uint64_t FixtureContentNow(void)
{
    struct timespec value;
    assert(clock_gettime(CLOCK_MONOTONIC, &value) == 0);
    return (uint64_t)value.tv_sec * 1000000000ULL + value.tv_nsec;
}

void __real_Sha256Hex(const unsigned char *data, int64_t size, unsigned char *digest);
void __wrap_Sha256Hex(const unsigned char *data, int64_t size, unsigned char *digest)
{
    if (atomic_load(&content_blocked)) {
        atomic_store(&content_entered, 1);
        while (atomic_load(&content_blocked)) usleep(1000);
    }
    __real_Sha256Hex(data, size, digest);
}

static const char *fixtures;
static char database[4096];
static int mode, starts;
static int bad_catalog;
static int shipped;
static int granted_starts;
static void *allocations[64];
static size_t allocation_count;

static String read_fixture(const char *name) {
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", fixtures, name);
    FILE *file = fopen(path, "rb");
    assert(file);
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    rewind(file);
    char *data = malloc((size_t)size);
    assert(data && fread(data, 1, (size_t)size, file) == (size_t)size);
    fclose(file);
    assert(allocation_count < 64);
    allocations[allocation_count++] = data;
    return StringView(data, (size_t)size);
}
String FixtureCatalog(void) { return read_fixture("catalog.json"); }
AssetView FixtureAsset(String path) {
    AssetView result = {0};
    if (StringEqual(path, StringLiteral("assets/practices/catalog.json"))) {
        static String catalog;
        if (!catalog.data) catalog = FixtureCatalog();
        result.data = bad_catalog ? StringLiteral("{\"schema\":1,\"packs\":[]}") : catalog;
        result.found = true;
    } else if (shipped && StringEqual(path, StringLiteral("assets/practices/default/whm.zib"))) {
        static String pack;
        if (!pack.data) pack = read_fixture("default-whm.zib");
        result.data = pack;
        result.found = true;
    } else if (shipped && StringEqual(path, StringLiteral("assets/practices/shipped/patterns.zib"))) {
        static String pack;
        if (!pack.data) pack = read_fixture("shipped-patterns.zib");
        result.data = pack;
        result.found = true;
    } else if (StringEqual(path, StringLiteral("locales/index.txt"))) {
        result.data = StringLiteral("en|English\nes|Español\n");
        result.found = true;
    }
    return result;
}
void FixtureMode(int32_t value) { mode = value; }
void FixtureCatalogMode(int32_t value) { bad_catalog = value; }
void FixtureShipped(int32_t value) { shipped = value; }
int32_t FixtureGrantedStarts(void) { return granted_starts; }
int32_t FixtureStarts(void) { return starts; }
bool FixtureTaiChiSaved(void) {
    char path[4096];
    snprintf(path, sizeof path, "%s/cache/packages/practice-taichi.zib", fixtures);
    return access(path, F_OK) == 0;
}
String __wrap_storage_db_path(void) { return StringView(database, strlen(database)); }
EmbeddedAssetEntry *asset_entry_at(size_t index) { (void)index; return NULL; }
size_t asset_entry_total(void) { return 0; }
void app_web_storage_flush(void) {}

bool __wrap_file_download_FileDownloadStart(FileDownload *download, String url, String destination) {
    const char prefix[] = "https://api.waozi.xyz/api/v2/packages/inbe.practices/";
    const char grant[] = "/fixture-grant";
    // A paid pack's grant is the last path segment; free packs have none.
    if (url.length == sizeof prefix - 1 + 64 + 4 + sizeof grant - 1) {
        assert(memcmp(url.data + sizeof prefix - 1 + 68, grant, sizeof grant - 1) == 0);
        granted_starts++;
    } else {
        assert(url.length == sizeof prefix - 1 + 64 + 4);
    }
    assert(memcmp(url.data, prefix, sizeof prefix - 1) == 0);
    char name[69];
    memcpy(name, url.data + sizeof prefix - 1, 68);
    name[68] = 0;
    String bytes = read_fixture(name);
    assert(bytes.length == download->maximum_bytes);
    snprintf((char *)download->destination, sizeof download->destination,
             "%.*s", (int)destination.length, destination.data);
    FILE *file = fopen((char *)download->destination, "wb");
    assert(file);
    assert(fwrite(bytes.data, 1, bytes.length, file) == bytes.length);
    if (mode == 1) { fseek(file, -1, SEEK_END); fputc(bytes.data[bytes.length - 1] ^ 1, file); }
    fclose(file);
    download->status = FileDownloadStatus_Downloading;
    starts++;
    return true;
}
FileDownloadStatus __wrap_file_download_FileDownloadPoll(FileDownload *download) {
    download->status = mode == 2 ? FileDownloadStatus_Error : FileDownloadStatus_Ready;
    return download->status;
}
void __wrap_file_download_FileDownloadRelease(FileDownload *download) { download->handle = 0; }

int main(int argc, char **argv) {
    assert(argc == 2);
    fixtures = argv[1];
    snprintf(database, sizeof database, "%s/cache/inbe.db", fixtures);
    int result = CheckPracticeDownloads();
    if (result) fprintf(stderr, "Practice downloads failed at check %d\n", result);
    for (size_t index = 0; index < allocation_count; index++) free(allocations[index]);
    return result != 0;
}
