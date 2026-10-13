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
extern int32_t FixtureHabitsSequence(void);

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
bool CellsValidatePackage(int32_t index, String bytes) {
    assert((index == 0 || index == 4) && bytes.length > 8);
    return true; /* The capability decoder is covered by cells-test. */
}

/* Wraps daochi-client's SecureRandom so the device bucket is fixed. */
int32_t __wrap_SecureRandom(uint8_t *output, int64_t length) {
    for (int64_t index = 0; index < length; index++) {
        output[index] = (uint8_t)(index * 37 + 11);
    }
    return 1;
}

static char latest_query[128];

bool __wrap_file_download_FileDownloadStart(FileDownload *download, String url, String destination) {
    assert(url.length > 0 && destination.length < sizeof(download->destination));
    assert(download->maximum_bytes > 0);
    /* Release checks name this host's interfaces and keep one device bucket. */
    char target[512];
    snprintf(target, sizeof(target), "%.*s", (int)destination.length, destination.data);
    if (strstr(target, ".download.json")) {
        char text[512];
        snprintf(text, sizeof(text), "%.*s", (int)url.length, url.data);
        const char *query = strstr(text, "/latest?host_api=");
        assert(query && strstr(query, "&module_api=") && strstr(query, "&bucket="));
        assert(!latest_query[0] || strcmp(latest_query, query) == 0);
        snprintf(latest_query, sizeof(latest_query), "%s", query);
    }
    snprintf((char *)download->destination, sizeof(download->destination), "%.*s", (int)destination.length, destination.data);
    download->status = FileDownloadStatus_Downloading;
    download->handle = (uint64_t)++starts;
    return true;
}
FileDownloadStatus __wrap_file_download_FileDownloadPoll(FileDownload *download) {
    if (held) {
        return FileDownloadStatus_Downloading;
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
    download->status = FileDownloadStatus_Ready;
    return download->status;
}
void __wrap_file_download_FileDownloadRelease(FileDownload *download) {
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
    pump();
    assert(starts == 0); /* Unasked means no implicit request. */
    assert(!package_manager_PackageAutomaticEnabled());
    package_manager_PackageSetAutomatic(false);
    pump();
    assert(starts == 0); /* Off means no implicit request. */
    int32_t baseline = FixtureHabitsSequence();
    assert(package_manager_PackageSequence(2) == baseline);
    storage_set_setting_int(StringLiteral("package_sequence_habits"), -10);
    assert(package_manager_PackageSequence(2) == baseline); /* Installed baseline is the floor. */
    request(); /* A manual check reuses the bundled cell at the same sequence. */
    assert(package_manager_PackageStatus(4) == 2 && starts == 1);
    int32_t installed_sequence = package_manager_PackageSequence(4);
    assert(installed_sequence > 0);
    String installed = package_manager_PackageInstalledBytes(4);
    assert(installed.length == 0); /* The offline bundle needs no disk cache. */
    assert(package_manager_PackageAvailable(4));
    manifest = "diary-new";
    request();
    assert(package_manager_PackageSequence(4) == installed_sequence + 1);
    installed = package_manager_PackageInstalledBytes(4);
    assert(installed.length > 8);
    free((void *)installed.data);
    manifest = "diary";
    request(); /* A correctly signed older manifest must still fail. */
    assert(package_manager_PackageStatus(4) == 3 && package_manager_PackageSequence(4) == installed_sequence + 1);
    manifest = "diary-bad";
    request();
    assert(package_manager_PackageStatus(4) == 3 && package_manager_PackageSequence(4) == installed_sequence + 1);
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
    held = false;

    /* A downloaded package proves itself by running; an unproven one that
       three starts in a row never proved is set aside for the bundled one. */
    package_trial_counted[4] = false;
    String trial = package_manager_PackageInstalledBytes(4);
    assert(trial.length > 8 && package_manager_PackageTrialAllows(4));
    free((void *)trial.data);
    package_manager_PackageTrialsProve(package_started_at + 9);
    assert(package_trials_open); /* Not proven before ten seconds. */
    package_manager_PackageTrialsProve(package_started_at + 10);
    assert(!package_trials_open);
    for (int start = 0; start < 5; start++) {
        package_trial_counted[4] = false;
        trial = package_manager_PackageInstalledBytes(4);
        assert(trial.length > 8 && package_manager_PackageTrialAllows(4)); /* Proven stays good. */
        free((void *)trial.data);
    }
    storage_set_setting_text(StringLiteral("package_good_diary"), StringLiteral(""));
    for (int start = 0; start < 3; start++) {
        package_trial_counted[4] = false;
        trial = package_manager_PackageInstalledBytes(4);
        assert(trial.length > 8 && package_manager_PackageTrialAllows(4));
        free((void *)trial.data);
    }
    package_trial_counted[4] = false;
    trial = package_manager_PackageInstalledBytes(4);
    assert(trial.length > 8 && !package_manager_PackageTrialAllows(4));
    free((void *)trial.data);
    assert(!package_manager_PackageTrialAllows(4)); /* Set aside for this process too. */
    int before_set_aside = starts;
    manifest = "diary-new";
    request(); /* The set-aside release is not downloaded again. */
    assert(package_manager_PackageStatus(4) == 2 && starts == before_set_aside + 1);

    /* Checks run daily, once after a start an hour after the last one, and
       ten minutes after a sync reports a newer root package. */
    storage_set_setting_int(StringLiteral("package_sequence_hint"), 0);
    package_last_check = 200000;
    package_hint_read_at = 0;
    package_launch_checked = false;
    assert(!package_manager_PackageCheckDue(201000));
    package_launch_checked = false;
    assert(package_manager_PackageCheckDue(203600));
    assert(!package_manager_PackageCheckDue(203700)); /* Once per start. */
    assert(package_manager_PackageCheckDue(286400));
    storage_set_setting_int(StringLiteral("package_sequence_hint"), 1000000);
    package_hint_read_at = 0;
    assert(!package_manager_PackageCheckDue(200300));
    assert(package_manager_PackageCheckDue(200700));
    storage_set_setting_int(StringLiteral("package_sequence_hint"), 1);
    package_hint_read_at = 0;
    assert(!package_manager_PackageCheckDue(200800)); /* Not newer than the installed root. */
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
