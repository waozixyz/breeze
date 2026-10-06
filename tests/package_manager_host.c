#include "package_manager.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const char *fixtures;
static char database[4096];
static char keys[32][128];
static char values[32][128];
static int setting_count;
static int starts;
static int releases;
static bool held;
static const char *manifest = "diary";
static EmbeddedAssetEntry publisher;

static String load(const char *name) {
    char path[4096];
    snprintf(path, sizeof(path), "%s/%s", fixtures, name);
    FILE *file = fopen(path, "rb");
    assert(file && !fseek(file, 0, SEEK_END));
    long size = ftell(file);
    assert(size > 0 && !fseek(file, 0, SEEK_SET));
    char *data = malloc((size_t)size);
    assert(data && fread(data, 1, (size_t)size, file) == (size_t)size);
    fclose(file);
    return StringView(data, (size_t)size);
}

static int setting(String key) {
    for (int index = 0; index < setting_count; index++) {
        if (StringEqual(key, StringView(keys[index], strlen(keys[index])))) {
            return index;
        }
    }
    assert(setting_count < 32 && key.length < sizeof(keys[0]));
    int index = setting_count++;
    memcpy(keys[index], key.data, key.length);
    return index;
}

int32_t storage_get_setting_int(String key, int32_t fallback) {
    const char *value = values[setting(key)];
    return *value ? atoi(value) : fallback;
}
String storage_get_setting_text(String key) {
    char *value = values[setting(key)];
    return StringView(value, strlen(value));
}
void storage_set_setting_int(String key, int32_t value) {
    snprintf(values[setting(key)], sizeof(values[0]), "%d", value);
}
void storage_set_setting_text(String key, String value) {
    assert(value.length < sizeof(values[0]));
    snprintf(values[setting(key)], sizeof(values[0]), "%.*s", (int)value.length, value.data);
}
String __wrap_storage_db_path(void) {
    return StringView(database, strlen(database));
}
EmbeddedAssetEntry *asset_entry_at(size_t index) {
    return index == 0 ? &publisher : NULL;
}
size_t asset_entry_total(void) {
    return 1;
}
void app_web_storage_flush(void) {
}
bool SubappsValidatePackage(int32_t index, String bytes) {
    assert((index == 0 || index == 4) && bytes.length > 8);
    return true; /* The capability decoder is covered by subapps-test. */
}

int32_t __wrap_DownloadRuntimeAsset(AssetDownload *download, String url, String destination) {
    assert(url.length > 0 && destination.length < sizeof(download->destination));
    assert(download->maximum_bytes > 0);
    snprintf((char *)download->destination, sizeof(download->destination), "%.*s", (int)destination.length, destination.data);
    download->status = AssetDownloadStatus_Downloading;
    download->handle = (uint64_t)++starts;
    return 1;
}
AssetDownloadStatus __wrap_PollRuntimeAssetDownload(AssetDownload *download) {
    if (held) {
        return AssetDownloadStatus_Downloading;
    }
    const char *destination = (char *)download->destination;
    const char *name = strstr(destination, ".download.json") ? manifest :
                       (package_index == 0 ? "root-bytes" : "diary-bytes");
    String data = load(name);
    assert(data.length <= download->maximum_bytes);
    FILE *output = fopen(destination, "wb");
    assert(output && fwrite(data.data, 1, data.length, output) == data.length);
    fclose(output);
    free((void *)data.data);
    download->status = AssetDownloadStatus_Ready;
    return download->status;
}
void __wrap_ReleaseRuntimeAssetDownload(AssetDownload *download) {
    if (download->handle) {
        releases++;
    }
    memset(download, 0, sizeof(*download));
}
static void pump(void) {
    package_manager_PackagePump(8, 200000);
}
static void request(void) {
    package_manager_PackageRequest(4);
    pump();
    pump();
    pump();
}

int32_t RunPackageManagerFixture(void) {
    package_manager_PackageSetAutomatic(false);
    pump();
    assert(starts == 0); /* Off means no implicit request. */
    assert(package_manager_PackageSequence(2) == 1);
    storage_set_setting_int(StringLiteral("package_sequence_habits"), -10);
    assert(package_manager_PackageSequence(2) == 1); /* Installed baseline is the floor. */
    request(); /* Manual installation is allowed with automatic updates off. */
    assert(package_manager_PackageStatus(4) == 2 && starts == 2);
    assert(package_manager_PackageSequence(4) == 1);
    String installed = package_manager_PackageInstalledBytes(4);
    assert(installed.length > 8);
    free((void *)installed.data);
    assert(package_manager_PackageAvailable(4));
    manifest = "diary-new";
    request();
    assert(package_manager_PackageSequence(4) == 2);
    manifest = "diary";
    request(); /* A correctly signed older manifest must still fail. */
    assert(package_manager_PackageStatus(4) == 3 && package_manager_PackageSequence(4) == 2);
    manifest = "diary-bad";
    request();
    assert(package_manager_PackageStatus(4) == 3 && package_manager_PackageSequence(4) == 2);
    installed = package_manager_PackageInstalledBytes(4);
    assert(installed.length > 8);
    free((void *)installed.data);
    manifest = "diary-new";
    char pointer[4096];
    snprintf(pointer, sizeof(pointer), "%s/packages/diary.current.json", fixtures);
    assert(unlink(pointer) == 0);
    request(); /* Same signed sequence/hash repairs a missing current pointer. */
    assert(package_manager_PackageStatus(4) == 2 && access(pointer, R_OK) == 0);
    manifest = "root-new";
    package_manager_PackageMarkRootActive(false);
    package_manager_PackageRequest(0);
    pump();
    pump();
    pump();
    assert(package_manager_PackageRootPending());
    installed = package_manager_PackageInstalledBytes(0);
    assert(installed.length > 8);
    free((void *)installed.data);
    package_manager_PackageMarkRootActive(true); /* Restart activates the cached root. */
    assert(!package_manager_PackageRootPending());
    assert(StringEqual(package_manager_PackageVersion(2), StringLiteral("1.1.0")));
    assert(StringEqual(package_manager_PackageVersion(3), StringLiteral("1.2.0")));
    held = true;
    package_manager_PackageSetAutomatic(true);
    pump(); /* Starts root automatic check. */
    assert(package_automatic && package_index == 0);
    package_manager_PackageRequest(4); /* A manual request survives disabling updates. */
    int cancelled = releases;
    package_manager_PackageSetAutomatic(false);
    assert(package_index == -1 && releases == cancelled + 1 && package_requested[4]);
    pump();
    assert(package_index == 4 && !package_automatic);
    package_manager_PackageSetAutomatic(false);
    assert(package_index == 4); /* In-flight manual work also survives. */
    package_manager_PackageCancel();
    return 0;
}
extern int32_t CheckPackageManager(void);
int main(int argc, char **argv) {
    assert(argc == 2);
    fixtures = argv[1];
    snprintf(database, sizeof(database), "%s/inbe.db", fixtures);
    String data = load("publishers.json");
    publisher = (EmbeddedAssetEntry){(uint8_t *)"apps/publishers.json", (uint8_t *)"application/json", (uint8_t *)data.data, data.length};
    int result = CheckPackageManager();
    free((void *)data.data);
    return result;
}
