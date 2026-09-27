#include "sync_account.h"
#include "storage.h"
#include "db.h"

#include <dirent.h>
#include <sqlite3.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int g_failures = 0;
static char g_data_root[1024] = "";

void
data_init(void)
{
}

const char *
data_root(void)
{
    return g_data_root;
}

void
TraceLog(int log_level, const char *text, ...)
{
    (void)log_level;
    (void)text;
}

void
sync_client_clear_auth_token(void)
{
}

char *
LoadFileText(const char *file_name)
{
    FILE *file;
    long size;
    char *text;

    file = fopen(file_name, "rb");
    if(file == NULL)
        return NULL;
    if(fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }
    size = ftell(file);
    if(size < 0) {
        fclose(file);
        return NULL;
    }
    rewind(file);
    text = (char *)malloc((size_t)size + 1);
    if(text == NULL) {
        fclose(file);
        return NULL;
    }
    if(fread(text, 1, (size_t)size, file) != (size_t)size) {
        free(text);
        fclose(file);
        return NULL;
    }
    text[size] = '\0';
    fclose(file);
    return text;
}

void
UnloadFileText(char *text)
{
    free(text);
}

bool
SaveFileData(const char *file_name, const void *data, int data_size)
{
    FILE *file;
    int ok;

    file = fopen(file_name, "wb");
    if(file == NULL)
        return 0;
    ok = fwrite(data, 1, (size_t)data_size, file) == (size_t)data_size;
    fclose(file);
    return ok;
}

static void
check_true(const char *label, int ok)
{
    if(ok)
        return;
    fprintf(stderr, "FAIL %s\n", label);
    g_failures++;
}

static void
check_false(const char *label, int ok)
{
    if(!ok)
        return;
    fprintf(stderr, "FAIL %s\n", label);
    g_failures++;
}

static void
check_str(const char *label, const char *got, const char *want)
{
    if(got != NULL && want != NULL && strcmp(got, want) == 0)
        return;
    fprintf(stderr, "FAIL %s: got %s, want %s\n",
            label, got != NULL ? got : "(null)", want != NULL ? want : "(null)");
    g_failures++;
}

static int
ensure_dir(const char *path)
{
    struct stat st;
    if(stat(path, &st) == 0 && S_ISDIR(st.st_mode))
        return 1;
    return mkdir(path, 0700) == 0;
}

static void
remove_tree(const char *path)
{
    DIR *dir = opendir(path);
    struct dirent *entry;

    if(dir == NULL) {
        remove(path);
        return;
    }
    while((entry = readdir(dir)) != NULL) {
        char child[1024];
        if(strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
            continue;
        snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
        remove_tree(child);
    }
    closedir(dir);
    rmdir(path);
}

static void
make_clean_root(char *out, size_t out_size, const char *name)
{
    snprintf(out, out_size, "/tmp/breathing-sync-account-test-%ld-%s", (long)getpid(), name);
    remove_tree(out);
    check_true("create test root", ensure_dir(out));
    snprintf(g_data_root, sizeof(g_data_root), "%s", out);
}

static void *
read_short_setting(void *unused)
{
    int *ok = (int *)unused;
    const char *value = storage_get_setting_text("sync_enabled");
    *ok = value != NULL && strcmp(value, "1") == 0;
    return NULL;
}

static void *
begin_and_commit_transaction(void *unused)
{
    int *result = (int *)unused;
    int ok = exec_sql("BEGIN IMMEDIATE");
    if(ok)
        ok = exec_sql("COMMIT");
    *result = ok;
    return NULL;
}

static void
test_parallel_setting_reads_and_transactions(void)
{
    char root[1024];
    char key[5121];
    pthread_t worker;
    int result = 0;
    int started;
    const char *main_value;

    make_clean_root(root, sizeof(root), "parallel-storage");
    check_true("open parallel storage", storage_init(root));
    memset(key, 'a', sizeof(key) - 1);
    key[sizeof(key) - 1] = '\0';
    storage_set_setting_text("sync_private_key", key);
    storage_set_setting_text("sync_enabled", "1");
    main_value = storage_get_setting_text("sync_private_key");
    check_true("main thread reads full recovery key",
               main_value != NULL && strlen(main_value) == 5120);
    started = pthread_create(&worker, NULL, read_short_setting, &result) == 0;
    check_true("start parallel setting read", started);
    if(started)
        pthread_join(worker, NULL);
    check_true("parallel setting read succeeds", result == 1);
    check_true("parallel read preserves recovery key buffer",
               main_value != NULL && strcmp(main_value, key) == 0);

    check_true("main transaction begins", exec_sql("BEGIN IMMEDIATE"));
    result = 0;
    started = pthread_create(&worker, NULL, begin_and_commit_transaction, &result) == 0;
    check_true("start parallel transaction", started);
    usleep(20000);
    check_true("main transaction commits", exec_sql("COMMIT"));
    if(started)
        pthread_join(worker, NULL);
    check_true("parallel transaction waits and commits", result == 1);
    storage_close();
    remove_tree(root);
}

static void
bytes_to_hex_local(const unsigned char *bytes, size_t len, char *out, size_t out_size)
{
    static const char hex[] = "0123456789abcdef";

    check_true("hex output size", out_size >= len * 2 + 1);
    for(size_t i = 0; i < len; i++) {
        out[i * 2] = hex[bytes[i] >> 4];
        out[i * 2 + 1] = hex[bytes[i] & 0x0f];
    }
    out[len * 2] = '\0';
}

static void
write_key_file(const char *path, const char *public_id,
               const char *public_key, const char *private_key)
{
    FILE *file = fopen(path, "wb");

    check_true("open key file", file != NULL);
    if(file == NULL)
        return;
    fprintf(file,
            "breathing-sync-key-v1\nalgorithm=ML-DSA-44\npublic_id=%s\npublic_key=%s\nprivate_key=%s\n",
            public_id, public_key, private_key);
    fclose(file);
}

static void
exec_db_sql(const char *label, const char *sql)
{
    sqlite3 *db = NULL;
    char *error = NULL;

    check_true(label, sqlite3_open(storage_db_path(), &db) == SQLITE_OK);
    if(db == NULL)
        return;
    if(sqlite3_exec(db, sql, NULL, NULL, &error) != SQLITE_OK) {
        fprintf(stderr, "FAIL %s: %s\n", label, error != NULL ? error : "sqlite error");
        sqlite3_free(error);
        g_failures++;
    }
    sqlite3_close(db);
}

static int
read_db_count(const char *sql)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int count = -1;

    if(sqlite3_open(storage_db_path(), &db) != SQLITE_OK || db == NULL)
        return count;
    if(sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK &&
       sqlite3_step(stmt) == SQLITE_ROW)
        count = sqlite3_column_int(stmt, 0);
    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return count;
}

static void
make_account_values(char public_id[65], char public_key_hex[2625],
                    char private_key_hex[5121])
{
    unsigned char public_key[1312];
    unsigned char private_key[2560];

    for(size_t i = 0; i < sizeof(public_key); i++)
        public_key[i] = (unsigned char)(i * 31U + 7U);
    for(size_t i = 0; i < sizeof(private_key); i++)
        private_key[i] = (unsigned char)(i * 17U + 3U);

    sync_sha256_hex(public_key, sizeof(public_key), public_id);
    bytes_to_hex_local(public_key, sizeof(public_key), public_key_hex, 2625);
    bytes_to_hex_local(private_key, sizeof(private_key), private_key_hex, 5121);
}

static void
make_account_values_variant(int variant, char public_id[65],
                            char public_key_hex[2625],
                            char private_key_hex[5121])
{
    unsigned char public_key[1312];
    unsigned char private_key[2560];

    for(size_t i = 0; i < sizeof(public_key); i++)
        public_key[i] = (unsigned char)(i * 31U + 7U + (unsigned)variant);
    for(size_t i = 0; i < sizeof(private_key); i++)
        private_key[i] = (unsigned char)(i * 17U + 3U + (unsigned)(variant * 3));

    sync_sha256_hex(public_key, sizeof(public_key), public_id);
    bytes_to_hex_local(public_key, sizeof(public_key), public_key_hex, 2625);
    bytes_to_hex_local(private_key, sizeof(private_key), private_key_hex, 5121);
}

static SyncAccountSaveResult
import_key_and_save(SyncAccount *account, const char *path, int clear_local_data)
{
    if(!sync_account_import_private_key_preview(account, path))
        return SYNC_ACCOUNT_SAVE_FAILED;
    return sync_account_save(account, clear_local_data);
}

static void
test_import_export_clear(void)
{
    char root[512];
    char key_path[1024];
    char export_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;
    char *exported;
    FILE *file;

    make_clean_root(root, sizeof(root), "roundtrip");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    snprintf(export_path, sizeof(export_path), "%s/exported.key", root);
    make_account_values(public_id, public_key, private_key);
    write_key_file(key_path, public_id, public_key, private_key);

    check_true("init storage", storage_init(root));
    storage_set_setting_text("sync_account_alias", "old-alias");
    check_true("import key",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_str("import public id", account.public_id, public_id);
    check_true("import clears stale alias",
               storage_get_setting_text("sync_account_alias") == NULL);
    check_true("load imported key", sync_account_load(&account));
    check_str("load public key", account.public_key_hex, public_key);
    check_str("load private key", account.private_key_hex, private_key);

    check_true("export key", sync_account_export_private_key(&account, export_path));
    exported = LoadFileText(export_path);
    check_true("read exported key", exported != NULL);
    if(exported != NULL) {
        check_true("export uses generic key header",
                   strstr(exported, "account-key-v1\n") == exported);
        check_true("export includes public key", strstr(exported, "\npublic_key=") != NULL);
        UnloadFileText(exported);
    }

    check_true("clear key", sync_account_clear());
    check_false("load after clear", sync_account_load(&account));
    check_true("import exported key",
               import_key_and_save(&account, export_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_str("reimport public id", account.public_id, public_id);

    file = fopen(key_path, "wb");
    check_true("open secret key alias file", file != NULL);
    if(file != NULL) {
        fprintf(file,
                "breathing-sync-key-v1\nalgorithm=ML-DSA-44\npublic_key=%s\nsecret_key=%s\n",
                public_key, private_key);
        fclose(file);
    }
    check_true("import secret key alias",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_str("derive public id", account.public_id, public_id);

    file = fopen(key_path, "wb");
    check_true("open exported key json file", file != NULL);
    if(file != NULL) {
        fprintf(file,
                "{\"exported_key\":\"breathing-sync-key-v1\\nalgorithm=ML-DSA-44\\npublic_id=%s\\npublic_key=%s\\nprivate_key=%s\\n\"}\n",
                public_id, public_key, private_key);
        fclose(file);
    }
    check_true("import exported key json",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_str("json public key", account.public_key_hex, public_key);

    storage_close();
    remove_tree(root);
}

static void
test_reject_invalid_keys(void)
{
    char root[512];
    char key_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;
    FILE *file;

    make_clean_root(root, sizeof(root), "invalid");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    make_account_values(public_id, public_key, private_key);

    check_true("init invalid storage", storage_init(root));

    public_id[0] = public_id[0] == '0' ? '1' : '0';
    write_key_file(key_path, public_id, public_key, private_key);
    check_false("reject mismatched public id",
                sync_account_import_private_key_preview(&account, key_path));

    file = fopen(key_path, "wb");
    check_true("open missing public key file", file != NULL);
    if(file != NULL) {
        fprintf(file,
                "breathing-sync-key-v1\nalgorithm=ML-DSA-44\npublic_id=%s\nprivate_key=%s\n",
                public_id, private_key);
        fclose(file);
    }
    check_false("reject missing public key",
                sync_account_import_private_key_preview(&account, key_path));
    check_false("no account after rejected imports", sync_account_load(&account));

    storage_close();
    remove_tree(root);
}

static void
test_legacy_synced_account_migrates_connected_server(void)
{
    char root[512];
    char key_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;

    make_clean_root(root, sizeof(root), "legacy-connected-flag");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    make_account_values(public_id, public_key, private_key);
    write_key_file(key_path, public_id, public_key, private_key);

    check_true("init legacy connected storage", storage_init(root));
    check_true("save legacy connected account",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    storage_set_setting_text("sync_server_url", "https://api.waozi.xyz");
    exec_db_sql("prepare legacy connected sync state",
                "INSERT OR REPLACE INTO meta(key,value) "
                "VALUES('sync_last_server_version','6638');"
                "INSERT OR REPLACE INTO meta(key,value) "
                "VALUES('sync_full_upload_done','1');"
                "DELETE FROM settings WHERE key IN ('sync_server_connected','sync_enabled');");
    storage_close();

    check_true("reopen legacy connected storage", storage_init(root));
    check_true("legacy connected flag migrated",
               storage_get_setting_int("sync_enabled", 0) == 1);
    check_true("legacy connected helper", storage_sync_enabled());

    storage_close();
    remove_tree(root);
}

static void
test_unsynced_account_does_not_migrate_connected_server(void)
{
    char root[512];
    char key_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;

    make_clean_root(root, sizeof(root), "unsynced-connected-flag");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    make_account_values(public_id, public_key, private_key);
    write_key_file(key_path, public_id, public_key, private_key);

    check_true("init unsynced connected storage", storage_init(root));
    check_true("save unsynced connected account",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    storage_set_setting_text("sync_server_url", "https://api.waozi.xyz");
    exec_db_sql("remove unsynced connected flag",
                "DELETE FROM settings WHERE key IN ('sync_server_connected','sync_enabled');");
    storage_close();

    check_true("reopen unsynced connected storage", storage_init(root));
    check_true("unsynced account remains disconnected",
               storage_get_setting_int("sync_enabled", 0) == 0);
    check_false("unsynced account helper disconnected",
                storage_sync_enabled());

    storage_close();
    remove_tree(root);
}

static void
test_disconnected_account_reports_queue_without_connection(void)
{
    char root[512];
    char key_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;
    StorageSyncStatus status;

    make_clean_root(root, sizeof(root), "disconnected-queued");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    make_account_values(public_id, public_key, private_key);
    write_key_file(key_path, public_id, public_key, private_key);

    check_true("init disconnected queued storage", storage_init(root));
    check_true("save disconnected queued account",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    storage_set_setting_text("sync_server_url", "https://api.waozi.xyz");
    storage_set_sync_enabled(0);
    exec_db_sql("insert disconnected queued sync row",
                "INSERT INTO sync_outbox(entity_type,entity_id,local_date,queued_at) "
                "VALUES('session','queued-local-session',0,strftime('%s','now'));");

    check_false("disconnected queued server helper",
                storage_sync_enabled());
    check_true("disconnected queued status loads",
               storage_sync_status(&status));
    check_true("disconnected queued has account", status.has_account);
    check_false("disconnected queued not connected", status.enabled);
    check_true("disconnected queued count visible", status.queued_changes == 1);
    check_true("disconnected queued row preserved",
               read_db_count("SELECT COUNT(*) FROM sync_outbox") == 1);

    storage_set_sync_enabled(1);
    storage_set_setting_int("sync_last_result", 6);
    storage_set_setting_int("sync_retry_attempt", 3);
    check_true("same key save succeeds", sync_account_save(&account, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_true("same key preserves retry", storage_get_setting_int("sync_retry_attempt", 0) == 3);
    check_true("same key preserves enabled sync", storage_sync_enabled());
    check_true("same key status", storage_sync_status(&status));
    storage_close();
    check_true("reopen retry state", storage_init(root));
    check_true("retry survives restart", storage_get_setting_int("sync_retry_attempt", 0) == 3);
    check_true("queue survives restart", storage_sync_status(&status) && status.queued_changes == 1);
    storage_set_sync_enabled(0);
    check_true("disconnect clears retry", storage_get_setting_int("sync_retry_attempt", -1) == 0);
    exec_db_sql("simulate explicit 1.9.19 disconnect",
                "DELETE FROM settings WHERE key='sync_enabled';"
                "INSERT OR REPLACE INTO settings(user_id,key,value,updated_at) "
                "SELECT id,'sync_server_connected','0',strftime('%s','now') FROM users LIMIT 1;");
    storage_close();
    check_true("open 1.9.19 disconnected account", storage_init(root));
    check_false("migration preserves explicit disconnect", storage_sync_enabled());
    exec_db_sql("simulate explicit 1.9.19 connection",
                "DELETE FROM settings WHERE key='sync_enabled';"
                "UPDATE settings SET value='1' WHERE key='sync_server_connected';");
    storage_close();
    check_true("open 1.9.19 connected account", storage_init(root));
    check_true("migration preserves enabled account", storage_sync_enabled());
    storage_close();
    remove_tree(root);
}

static void
test_imported_account_backfills_existing_local_data(void)
{
    char root[512];
    char key_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;
    char *payload;
    int rounds[] = {30, 45, 60};

    make_clean_root(root, sizeof(root), "account-backfill");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    make_account_values(public_id, public_key, private_key);
    write_key_file(key_path, public_id, public_key, private_key);

    check_true("init account backfill storage", storage_init(root));
    check_true("save existing local session",
               storage_save_session_at_for_activity(20260621, 8, 15, 0,
                                                    rounds, 3, 0, 1, NULL, 0));
    exec_db_sql("insert existing local habit",
                "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                "sync_mode,sync_activity,counter_enabled,sort_order,deleted_at,updated_at) "
                "VALUES('habit-local',(SELECT id FROM users LIMIT 1),'Existing Local Habit',"
                "64,128,192,1,1,1,0,0,strftime('%s','now'));"
                "INSERT INTO habit_days(habit_id,local_date,completed,count,updated_at) "
                "VALUES('habit-local',20260621,1,5,strftime('%s','now'));"
                "INSERT OR REPLACE INTO meta(key,value) VALUES('sync_last_server_version','44');"
                "INSERT OR REPLACE INTO meta(key,value) VALUES('sync_full_upload_done','1');"
                "INSERT OR REPLACE INTO meta(key,value) VALUES('sync_backfill_v2_done','1');"
                "DELETE FROM sync_outbox;");

    check_true("import account resets sync state",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_str("imported deterministic account", account.public_id, public_id);
    check_str("account owner marker", storage_sync_data_owner_public_id(), public_id);

    payload = storage_build_sync_payload_json(account.public_id, account.public_key_hex);
    check_true("account bootstrap payload built", payload != NULL);
    if(payload != NULL) {
        check_true("account bootstrap flag present", strstr(payload, "\"bootstrap\":true") != NULL);
        check_true("existing local habit uploaded",
                   strstr(payload, "Existing Local Habit") != NULL);
        check_true("existing local habit day uploaded",
                   strstr(payload, "\"local_date\":20260621") != NULL &&
                   strstr(payload, "\"count\":5") != NULL);
        check_true("existing local session uploaded",
                   strstr(payload, "\"entity_type\":\"session\"") != NULL &&
                   strstr(payload, "\"rounds\":[") != NULL);
        check_true("local settings still excluded",
                   strstr(payload, "\"preferences\"") == NULL &&
                   strstr(payload, "\"settings\"") == NULL);
    }
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_logout_preserves_data_owner(void)
{
    char root[512];
    char key_path[1024];
    char public_id[65];
    char public_key[2625];
    char private_key[5121];
    SyncAccount account;

    make_clean_root(root, sizeof(root), "logout-owner");
    snprintf(key_path, sizeof(key_path), "%s/breathing-sync.key", root);
    make_account_values(public_id, public_key, private_key);
    write_key_file(key_path, public_id, public_key, private_key);

    check_true("init logout owner storage", storage_init(root));
    check_true("import logout owner account",
               import_key_and_save(&account, key_path, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_str("owner before logout", storage_sync_data_owner_public_id(), public_id);
    check_true("logout account", sync_account_clear());
    check_false("credentials removed", sync_account_load(&account));
    check_str("owner after logout", storage_sync_data_owner_public_id(), public_id);
    check_true("logout clears sync outbox",
               read_db_count("SELECT COUNT(*) FROM sync_outbox") == 0);

    storage_close();
    remove_tree(root);
}

static void
test_different_account_requires_clear_local_data(void)
{
    char root[512];
    char key_path_one[1024];
    char key_path_two[1024];
    char public_id_one[65];
    char public_key_one[2625];
    char private_key_one[5121];
    char public_id_two[65];
    char public_key_two[2625];
    char private_key_two[5121];
    SyncAccount account;
    SyncAccount loaded;

    make_clean_root(root, sizeof(root), "account-switch");
    snprintf(key_path_one, sizeof(key_path_one), "%s/one.key", root);
    snprintf(key_path_two, sizeof(key_path_two), "%s/two.key", root);
    make_account_values_variant(0, public_id_one, public_key_one, private_key_one);
    make_account_values_variant(9, public_id_two, public_key_two, private_key_two);
    write_key_file(key_path_one, public_id_one, public_key_one, private_key_one);
    write_key_file(key_path_two, public_id_two, public_key_two, private_key_two);

    check_true("init account switch storage", storage_init(root));
    exec_db_sql("insert switch local habit",
                "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                "sync_mode,sync_activity,counter_enabled,sort_order,deleted_at,updated_at) "
                "VALUES('habit-switch',(SELECT id FROM users LIMIT 1),'Switch Habit',"
                "64,128,192,1,1,1,0,0,strftime('%s','now'));"
                "INSERT INTO habit_days(habit_id,local_date,completed,count,updated_at) "
                "VALUES('habit-switch',20260622,1,3,strftime('%s','now'));");

    check_true("first account binds data",
               import_key_and_save(&account, key_path_one, 0) == SYNC_ACCOUNT_SAVE_OK);
    check_true("logout before account switch", sync_account_clear());
    check_true("local syncable data remains", storage_has_local_syncable_data());

    check_true("second account blocked before clear",
               import_key_and_save(&account, key_path_two, 0) ==
                   SYNC_ACCOUNT_SAVE_NEEDS_CLEAR);
    check_false("blocked switch leaves no credentials", sync_account_load(&loaded));
    check_str("blocked switch keeps old owner", storage_sync_data_owner_public_id(),
              public_id_one);
    check_true("blocked switch keeps local data", storage_has_local_syncable_data());

    check_true("second account can clear local data",
               import_key_and_save(&account, key_path_two, 1) == SYNC_ACCOUNT_SAVE_OK);
    check_true("new account stored", sync_account_load(&loaded));
    check_str("new account public id", loaded.public_id, public_id_two);
    check_true("new account clears alias",
               storage_get_setting_text("sync_account_alias") == NULL);
    check_str("new owner after clear", storage_sync_data_owner_public_id(), public_id_two);
    check_false("local syncable data cleared", storage_has_local_syncable_data());

    storage_close();
    remove_tree(root);
}

static void
test_social_cache_does_not_block_account_switch(void)
{
    char root[512];
    char key_path_one[1024];
    char key_path_two[1024];
    char public_id_one[65];
    char public_key_one[2625];
    char private_key_one[5121];
    char public_id_two[65];
    char public_key_two[2625];
    char private_key_two[5121];
    SyncAccount account;
    SyncAccount loaded;

    make_clean_root(root, sizeof(root), "social-cache-account-switch");
    snprintf(key_path_one, sizeof(key_path_one), "%s/one.key", root);
    snprintf(key_path_two, sizeof(key_path_two), "%s/two.key", root);
    make_account_values_variant(1, public_id_one, public_key_one, private_key_one);
    make_account_values_variant(2, public_id_two, public_key_two, private_key_two);
    write_key_file(key_path_one, public_id_one, public_key_one, private_key_one);
    write_key_file(key_path_two, public_id_two, public_key_two, private_key_two);

    check_true("init social cache switch storage", storage_init(root));
    check_true("first social cache account",
               import_key_and_save(&account, key_path_one, 0) ==
                   SYNC_ACCOUNT_SAVE_OK);
    check_true("store social-only cache",
               storage_set_social_cache_json("friends.list",
                                             "{\"friends\":[{\"user_id_hash\":\"friend\"}]}"));
    check_false("social-only cache is not local syncable data",
                storage_has_local_syncable_data());
    check_true("logout social cache account", sync_account_clear());
    check_true("second social cache account saves without clear",
               import_key_and_save(&account, key_path_two, 0) ==
                   SYNC_ACCOUNT_SAVE_OK);
    check_true("second social cache account stored", sync_account_load(&loaded));
    check_str("second social cache owner", storage_sync_data_owner_public_id(),
              public_id_two);

    storage_close();
    remove_tree(root);
}

int
main(void)
{
    test_parallel_setting_reads_and_transactions();
    test_import_export_clear();
    test_reject_invalid_keys();
    test_legacy_synced_account_migrates_connected_server();
    test_unsynced_account_does_not_migrate_connected_server();
    test_disconnected_account_reports_queue_without_connection();
    test_imported_account_backfills_existing_local_data();
    test_logout_preserves_data_owner();
    test_different_account_requires_clear_local_data();
    test_social_cache_does_not_block_account_switch();

    if(g_failures != 0) {
        fprintf(stderr, "%d sync account test failure(s)\n", g_failures);
        return 1;
    }
    printf("sync account tests passed\n");
    return 0;
}
