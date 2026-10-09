#include "zir_string.h"
#include "ziran_host.h"
#include "sqlite3.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *payloads[10];
static size_t sizes[10];
static int32_t module_runs;
static bool use_cached_bundles;
static int32_t cached_reads[6];
static int32_t bundle_opens;
static int32_t instance_opens;
static bool corrupt_cached_lists;
static bool fail_next_instance;
static bool fail_next_run;

Bundle *__real_BundleOpenBytes(const unsigned char *data, size_t count);
Bundle *__wrap_BundleOpenBytes(const unsigned char *data, size_t count)
{
    bundle_opens++;
    return __real_BundleOpenBytes(data, count);
}

int32_t ModuleTestBundleOpens(void)
{
    return bundle_opens;
}

int32_t ModuleTestInstanceOpens(void)
{
    return instance_opens;
}

void ModuleTestCorruptCachedLists(bool enabled)
{
    corrupt_cached_lists = enabled;
}

BundleInstance *__real_BundleInstantiate(const Bundle *bundle,
    const HostBinding *bindings, size_t count);

static int unused_capability(void *context, const char *module,
    const char *function, const VmHostValue *arguments, int count,
    VmHostValue *result)
{
    (void)context;
    (void)module;
    (void)function;
    (void)arguments;
    (void)count;
    (void)result;
    return 0;
}

/* A wrapper without the frame inventory must reject the smaller package
 * before running it. The current host handshake is exercised by CheckModules. */
static void check_practice_inventory_capability(void)
{
    Bundle *bundle = BundleOpenBytes(payloads[2], sizes[2]);
    assert(bundle != NULL);
    size_t count = BundleCapabilityCount(bundle);
    assert(count > 2 && count <= 64);
    HostBinding bindings[64];
    size_t legacy_count = 0;
    size_t inventory_index = count;
    for(size_t i = 0; i < count; i++) {
        HostBinding binding = {
            BundleCapabilityModule(bundle, i),
            BundleCapabilityFunction(bundle, i), unused_capability, NULL
        };
        if(strcmp(binding.function, "SunSalutationStoredFrame") == 0) {
            assert(inventory_index == count);
            inventory_index = i;
        } else {
            bindings[legacy_count++] = binding;
        }
    }
    assert(inventory_index < count && legacy_count == count - 1);
    assert(__real_BundleInstantiate(bundle, bindings, legacy_count) == NULL);
    bindings[legacy_count] = (HostBinding){
        BundleCapabilityModule(bundle, inventory_index),
        BundleCapabilityFunction(bundle, inventory_index), unused_capability, NULL
    };
    BundleInstance *instance = __real_BundleInstantiate(bundle, bindings, count);
    assert(instance != NULL);
    BundleInstanceClose(instance);
    BundleClose(bundle);
}

void ModuleTestFailRun(void)
{
    fail_next_run = true;
}

void ModuleTestFailInstantiate(void)
{
    fail_next_instance = true;
}

BundleInstance *__wrap_BundleInstantiate(const Bundle *bundle,
    const HostBinding *bindings, size_t count)
{
    instance_opens++;
    if(fail_next_instance) {
        fail_next_instance = false;
        return NULL;
    }
    return __real_BundleInstantiate(bundle, bindings, count);
}

void ModuleTestUseCache(bool enabled)
{
    use_cached_bundles = enabled;
    memset(cached_reads, 0, sizeof(cached_reads));
}

int32_t ModuleTestCachedReads(int32_t index)
{
    assert(index >= 0 && index < 6);
    return cached_reads[index];
}

extern String __real_package_manager_PackageInstalledBytes(int32_t index);
String __wrap_package_manager_PackageInstalledBytes(int32_t index)
{
    if(!use_cached_bundles) {
        return __real_package_manager_PackageInstalledBytes(index);
    }
    assert(index >= 0 && index < 6);
    cached_reads[index]++;
    const int fixture[] = {5, 0, 1, 2, 8, 9};
    int source = fixture[index];
    if(index == 1 && corrupt_cached_lists) source = 7;
    char *copy = malloc(sizes[source]);
    assert(copy);
    memcpy(copy, payloads[source], sizes[source]);
    return StringView(copy, sizes[source]);
}

int __real_BundleInstanceRun(BundleInstance *instance, long long *result,
                             int *has_result);

int __wrap_BundleInstanceRun(BundleInstance *instance, long long *result,
                             int *has_result)
{
    module_runs++;
    if(fail_next_run) {
        fail_next_run = false;
        return 0;
    }
    return __real_BundleInstanceRun(instance, result, has_result);
}

int32_t ModuleTestRuns(void)
{
    return module_runs;
}

bool ModuleTestPackageBytes(void)
{
    Bundle *root = BundleOpenBytes(payloads[5], sizes[5]);
    if(root == NULL || BundleAssetCount(root) < 4) {
        BundleClose(root);
        return false;
    }
    const char *names[] = {"cells/lists.zib", "cells/habits.zib", "cells/practices.zib", "cells/diary.zib", "cells/lumi.zib"};
    bool matched[5] = {false};
    bool valid = true;
    for(size_t asset = 0; asset < BundleAssetCount(root); asset++) {
        bool found = false;
        for(size_t feature = 0; feature < 5; feature++) {
            if(strcmp(BundleAssetName(root, asset), names[feature]) != 0) {
                continue;
            }
            int payload = feature == 4 ? 9 : feature == 3 ? 8 : (int)feature;
            found = !matched[feature] && BundleAssetSize(root, asset) == sizes[payload] &&
                    memcmp(BundleAssetData(root, asset), payloads[payload], sizes[payload]) == 0;
            matched[feature] = found;
            Bundle *nested = BundleOpenBytes(BundleAssetData(root, asset), BundleAssetSize(root, asset));
            valid = valid && nested != NULL;
            BundleClose(nested);
        }
        if(strncmp(BundleAssetName(root, asset), "cells/", 8) == 0)
            valid = valid && found;
    }
    BundleClose(root);
    return valid && matched[0] && matched[1] && matched[2] && matched[3] && matched[4];
}

void app_web_storage_flush(void) {}

extern int32_t CheckModules(void);
extern void *storage_db_handle(void);

/* Startup failure fixtures expose no embedded assets and open no profile. */
void *asset_entry_at(size_t index)
{
    (void)index;
    return NULL;
}

size_t asset_entry_total(void)
{
    return 0;
}

String ModuleTestText(String name)
{
    const char *names[] = {"lists", "habits", "practice", "wrong-record", "wrong-scalar",
                           "inbe", "missing-assets", "invalid-nested", "diary", "lumi"};
    for(int i = 0; i < 10; i++) {
        if(StringEqual(name, StringView(names[i], strlen(names[i])))) {
            return StringView((char *)payloads[i], sizes[i]);
        }
    }
    return StringView("", 0);
}

int32_t ModuleTestCount(String sql)
{
    sqlite3_stmt *stmt = NULL;
    assert(sqlite3_prepare_v2(storage_db_handle(), sql.data, (int)sql.length,
                              &stmt, NULL) == SQLITE_OK);
    assert(sqlite3_step(stmt) == SQLITE_ROW);
    int result = sqlite3_column_int(stmt, 0);
    sqlite3_finalize(stmt);
    return result;
}

bool ModuleTestSeedOld(void)
{
    sqlite3 *old = NULL;
    assert(sqlite3_open("module-data/inbe.db", &old) == SQLITE_OK);
    FILE *file = fopen("schema-1.8.9.sql", "rb");
    assert(file != NULL);
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    rewind(file);
    char *sql = malloc((size_t)length + 1);
    assert(sql != NULL && fread(sql, 1, (size_t)length, file) == (size_t)length);
    sql[length] = 0;
    fclose(file);
    assert(sqlite3_exec(old, sql, NULL, NULL, NULL) == SQLITE_OK);
    free(sql);
    const char *fixture =
        "INSERT INTO users VALUES('module-user',1,'local');"
        "INSERT INTO meta VALUES('current_user_id','module-user');"
        "INSERT INTO settings VALUES('module-user','language','es',12);"
        "INSERT INTO sessions VALUES('old-session','module-user',10,20260925,0,0,'local',10,123,0,1);"
        "INSERT INTO session_rounds VALUES('old-session',0,35);"
        "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,sync_mode,sync_activity,sort_order,updated_at) VALUES('old-habit','module-user','Old habit',1,2,3,0,0,0,1);"
        "INSERT INTO habit_days VALUES('old-habit',20260925,1,1,0,1);";
    assert(sqlite3_exec(old, fixture, NULL, NULL, NULL) == SQLITE_OK);
    sqlite3_close(old);
    return true;
}

/* These tests deliberately exercise denied temporary-file creation. */
FILE *__wrap_tmpfile(void)
{
    return NULL;
}

int main(int argc, char **argv)
{
    assert(argc == 11);
    for(int i = 0; i < 10; i++) {
        FILE *file = fopen(argv[i + 1], "rb");
        assert(file != NULL);
        assert(fseek(file, 0, SEEK_END) == 0);
        long size = ftell(file);
        assert(size > 0 && fseek(file, 0, SEEK_SET) == 0);
        payloads[i] = malloc((size_t)size);
        sizes[i] = (size_t)size;
        assert(payloads[i] != NULL && fread(payloads[i], 1, sizes[i], file) == sizes[i]);
        fclose(file);
    }
    check_practice_inventory_capability();
    int result = CheckModules();
    for(int i = 0; i < 10; i++) {
        free(payloads[i]);
    }
    if(result != 0) {
        fprintf(stderr, "Module integration failed: %d\n", result);
    } else {
        puts("Root and five independent bundles: app selection, routes, edits, shared SQLite/identity, practices, migration/restart and invalid-schema handling passed");
    }
    return result != 0;
}
