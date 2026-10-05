#include "zir_string.h"
#include "ziran_host.h"
#include "sqlite3.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *payloads[8];
static size_t sizes[8];
static int32_t module_runs;

int __real_BundleInstanceRun(BundleInstance *instance, long long *result,
                             int *has_result);

int __wrap_BundleInstanceRun(BundleInstance *instance, long long *result,
                             int *has_result)
{
    module_runs++;
    return __real_BundleInstanceRun(instance, result, has_result);
}

int32_t ModuleTestRuns(void)
{
    return module_runs;
}

bool ModuleTestPackageBytes(void)
{
    Bundle *root = BundleOpenBytes(payloads[5], sizes[5]);
    if(root == NULL || BundleAssetCount(root) != 3) {
        BundleClose(root);
        return false;
    }
    const char *names[] = {"subapps/lists.zib", "subapps/habits.zib", "subapps/practice.zib"};
    bool matched[3] = {false, false, false};
    bool valid = true;
    for(size_t asset = 0; asset < BundleAssetCount(root); asset++) {
        bool found = false;
        for(size_t feature = 0; feature < 3; feature++) {
            if(strcmp(BundleAssetName(root, asset), names[feature]) != 0) {
                continue;
            }
            found = !matched[feature] && BundleAssetSize(root, asset) == sizes[feature] &&
                    memcmp(BundleAssetData(root, asset), payloads[feature], sizes[feature]) == 0;
            matched[feature] = found;
            Bundle *nested = BundleOpenBytes(BundleAssetData(root, asset), BundleAssetSize(root, asset));
            valid = valid && nested != NULL && BundleAssetCount(nested) == 0;
            BundleClose(nested);
        }
        valid = valid && found;
    }
    BundleClose(root);
    return valid && matched[0] && matched[1] && matched[2];
}

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
                           "inbe", "missing-assets", "invalid-nested"};
    for(int i = 0; i < 8; i++) {
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
    assert(argc == 9);
    for(int i = 0; i < 8; i++) {
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
    int result = CheckModules();
    for(int i = 0; i < 8; i++) {
        free(payloads[i]);
    }
    if(result != 0) {
        fprintf(stderr, "Module integration failed: %d\n", result);
    } else {
        puts("Root and three nested bundles: app selection, routes, edits, shared SQLite/identity, practices, migration/restart and invalid-schema handling passed");
    }
    return result != 0;
}
