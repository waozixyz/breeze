#include "kry_archive.h"
#include "kryon.h"
#include "habits/habit_types.h"
#include "habits/habit_model.h"
#include "src/screens/elist_types.h"
#include "storage.h"
#include <sqlite3.h>

#include <dirent.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static int g_failures = 0;
static int g_seen_topic = -1;
static int g_seen_activity = -1;

static void fill_test_private_key(char out[5121]);

void
data_init(void)
{
}

static void
check_int(const char *label, int got, int want)
{
    if(got == want)
        return;
    fprintf(stderr, "FAIL %s: got %d, want %d\n", label, got, want);
    g_failures++;
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
check_str(const char *label, const char *got, const char *want)
{
    if(got == NULL && want == NULL)
        return;
    if(got != NULL && want != NULL && strcmp(got, want) == 0)
        return;
    fprintf(stderr, "FAIL %s: got %s, want %s\n", label, got != NULL ? got : "(null)",
            want != NULL ? want : "(null)");
    g_failures++;
}

static int
ascii_equal_ci(const char *a, const char *b)
{
    unsigned char ca;
    unsigned char cb;

    if(a == NULL || b == NULL)
        return 0;
    while(*a != '\0' && *b != '\0') {
        ca = (unsigned char)*a++;
        cb = (unsigned char)*b++;
        if(ca >= 'A' && ca <= 'Z')
            ca = (unsigned char)(ca - 'A' + 'a');
        if(cb >= 'A' && cb <= 'Z')
            cb = (unsigned char)(cb - 'A' + 'a');
        if(ca != cb)
            return 0;
    }
    return *a == '\0' && *b == '\0';
}

static Habit *
find_habit_ci(Habits *habits, const char *name)
{
    if(habits == NULL || name == NULL)
        return NULL;
    for(int i = 0; i < habits->count; i++) {
        if(ascii_equal_ci(habits->items[i].name, name))
            return &habits->items[i];
    }
    return NULL;
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
make_path(char *out, size_t out_size, const char *root, const char *leaf)
{
    snprintf(out, out_size, "%s/%s", root, leaf);
}

static void
make_nested_dir(const char *root, const char *a, const char *b, const char *c)
{
    char path[512];

    make_path(path, sizeof(path), root, a);
    check_true("create nested dir a", ensure_dir(path));
    snprintf(path, sizeof(path), "%s/%s/%s", root, a, b);
    check_true("create nested dir b", ensure_dir(path));
    snprintf(path, sizeof(path), "%s/%s/%s/%s", root, a, b, c);
    check_true("create nested dir c", ensure_dir(path));
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
    snprintf(out, out_size, "/tmp/breathing-storage-test-%ld-%s", (long)getpid(), name);
    remove_tree(out);
    check_true("create test root", ensure_dir(out));
}

static void
write_source_database(const char *root)
{
    int rounds[] = {45, 60, 75};
    Habits habits;

    check_true("init source db", storage_init(root));
    check_true("save source session", storage_save_session(rounds, 3, NULL, 0));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habit_set_day(&habits, 0, 20260613, 1);
    habits_save(&habits);
    check_int("source sessions", storage_session_count(), 1);
    storage_close();
}

static void
insert_raw_habit_day(const char *root, const char *habit_id, int local_date, int completed)
{
    char db_path[512];
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open raw habit day db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db == NULL)
        return;
    if(sqlite3_prepare_v2(db,
                          "INSERT OR REPLACE INTO "
                          "habit_days(habit_id,local_date,completed,updated_at) "
                          "VALUES(?1,?2,?3,0)",
                          -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, habit_id, -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 2, local_date);
        sqlite3_bind_int(stmt, 3, completed ? 1 : 0);
        check_true("insert raw habit day", sqlite3_step(stmt) == SQLITE_DONE);
    } else {
        check_true("prepare raw habit day", 0);
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);
}

static int
read_raw_habit_day_count(const char *root, const char *habit_id, int local_date)
{
    char db_path[512];
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int count = -1;

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open raw count db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db == NULL)
        return count;
    if(sqlite3_prepare_v2(db, "SELECT count FROM habit_days WHERE habit_id=?1 AND local_date=?2",
                          -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, habit_id, -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 2, local_date);
        if(sqlite3_step(stmt) == SQLITE_ROW)
            count = sqlite3_column_int(stmt, 0);
    } else {
        check_true("prepare raw count", 0);
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return count;
}

static int
read_raw_count_query(const char *root, const char *sql)
{
    char db_path[512];
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int count = -1;

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open raw count query db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db == NULL)
        return count;
    if(sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        if(sqlite3_step(stmt) == SQLITE_ROW)
            count = sqlite3_column_int(stmt, 0);
    } else {
        check_true("prepare raw count query", 0);
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return count;
}

static int
read_raw_session_round_seconds(const char *root, const char *session_id, int round_index)
{
    char db_path[512];
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int seconds = -1;

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open raw session round db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db == NULL)
        return seconds;
    if(sqlite3_prepare_v2(db,
                          "SELECT seconds FROM session_rounds WHERE "
                          "session_id=?1 AND round_index=?2",
                          -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, session_id, -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 2, round_index);
        if(sqlite3_step(stmt) == SQLITE_ROW)
            seconds = sqlite3_column_int(stmt, 0);
    } else {
        check_true("prepare raw session round", 0);
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return seconds;
}

static void
test_sync_payload_omits_uploaded_state_after_upload_marker(void)
{
    char root[512];
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "sync-full-local-state");
    check_true("init sync watermark db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habit_set_day_count(&habits, 0, 20260612, 12);
    habits_save(&habits);

    storage_close();

    {
        char db_path[512];
        sqlite3 *db = NULL;
        sqlite3_stmt *stmt = NULL;
        long long updated_at = 0;
        make_path(db_path, sizeof(db_path), root, "inbe.db");
        check_true("open sync watermark raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
        if(db != NULL) {
            if(sqlite3_prepare_v2(db, "SELECT updated_at FROM habit_days WHERE local_date=20260612",
                                  -1, &stmt, NULL) == SQLITE_OK &&
               sqlite3_step(stmt) == SQLITE_ROW)
                updated_at = sqlite3_column_int64(stmt, 0);
            if(stmt != NULL)
                sqlite3_finalize(stmt);
            check_true("set sync watermark raw meta",
                       updated_at > 0 && sqlite3_exec(db,
                                                      "INSERT OR REPLACE INTO meta(key,value) "
                                                      "VALUES('sync_full_upload_done','1');",
                                                      NULL, NULL, NULL) == SQLITE_OK);
            check_true("set sync backfill marker raw meta",
                       sqlite3_exec(db,
                                    "INSERT OR REPLACE INTO meta(key,value) "
                                    "VALUES('sync_backfill_v2_done','1');",
                                    NULL, NULL, NULL) == SQLITE_OK);
            if(updated_at > 0) {
                char sql[192];
                snprintf(sql, sizeof(sql),
                         "INSERT OR REPLACE INTO meta(key,value) "
                         "VALUES('sync_last_upload_at','%lld');",
                         updated_at);
                check_true("set sync same second upload marker",
                           sqlite3_exec(db, sql, NULL, NULL, NULL) == SQLITE_OK);
            }
            check_true("clear uploaded outbox raw meta",
                       sqlite3_exec(db, "DELETE FROM sync_outbox;", NULL, NULL, NULL) == SQLITE_OK);
            sqlite3_close(db);
        }
    }

    check_true("reopen sync watermark db", storage_init(root));
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("habit day omitted from sync payload after upload marker",
               payload != NULL && strstr(payload, "\"local_date\":20260612") == NULL &&
                   strstr(payload, "\"count\":12") == NULL);
    storage_free_sync_payload_json(payload);
    storage_close();
    remove_tree(root);
}

static void
test_sync_backfill_includes_existing_habits(void)
{
    char root[512];
    char private_key[5121];
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "sync-existing-habit-backfill");
    check_true("init backfill sync db", storage_init(root));
    check_true("sync refuses payload without a private record key",
               storage_build_sync_payload_json("test-hash", "test-public-key") == NULL);
    fill_test_private_key(private_key);
    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", private_key);
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habits_save(&habits);

    storage_close();

    {
        char db_path[512];
        sqlite3 *db = NULL;
        make_path(db_path, sizeof(db_path), root, "inbe.db");
        check_true("open backfill raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
        if(db != NULL) {
            check_true("mark old full upload done",
                       sqlite3_exec(db,
                                    "INSERT OR REPLACE INTO meta(key,value) "
                                    "VALUES('sync_full_upload_done','1');",
                                    NULL, NULL, NULL) == SQLITE_OK);
            check_true("clear old outbox",
                       sqlite3_exec(db, "DELETE FROM sync_outbox;", NULL, NULL, NULL) == SQLITE_OK);
            sqlite3_close(db);
        }
    }

    check_true("reopen backfill sync db", storage_init(root));
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("existing habit included in encrypted sync backfill",
               payload != NULL &&
                   strstr(payload, "\"ops\":") == NULL &&
                   strstr(payload, "private.inbe.v1.habits") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_excludes_local_settings(void)
{
    char root[512];
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "sync-local-settings");
    check_true("init local settings sync db", storage_init(root));
    storage_set_setting_text("theme", "dark");
    storage_set_setting_text("main_tab", "0");
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("settings are not present in sync payload",
               payload != NULL && strstr(payload, "\"preferences\"") == NULL &&
                   strstr(payload, "\"theme\"") == NULL && strstr(payload, "\"main_tab\"") == NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_includes_queued_current_edits(void)
{
    char root[512];
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "sync-queued-edit");
    check_true("init queued sync db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habit_set_day_count(&habits, 0, 20260617, 7);
    habits_save(&habits);

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("queued habit day included in sync payload",
               payload != NULL && strstr(payload, "\"local_date\":20260617") != NULL &&
                   strstr(payload, "\"count\":7") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
fill_test_private_key(char out[5121])
{
    for(int i = 0; i < 5120; i++)
        out[i] = (i % 2) == 0 ? '4' : '2';
    out[5120] = '\0';
}

static void
test_sync_rejects_unencrypted_outbox_record(void)
{
    char root[512];
    char db_path[512];
    char private_key[5121];
    sqlite3 *db = NULL;
    StorageSyncStatus status;
    char *payload;

    make_clean_root(root, sizeof(root), "sync-unknown-record");
    check_true("init unknown record db", storage_init(root));
    fill_test_private_key(private_key);
    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", private_key);
    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open unknown record db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        check_true("queue unknown record",
                   sqlite3_exec(db,
                                "INSERT INTO sync_outbox(entity_type,entity_id,local_date,queued_at) "
                                "VALUES('unknown','record-1',0,1)",
                                NULL, NULL, NULL) == SQLITE_OK);
        sqlite3_close(db);
    }

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("unknown queued record rejects payload", payload == NULL);
    storage_free_sync_payload_json(payload);
    memset(&status, 0, sizeof(status));
    check_true("unknown record status remains available", storage_sync_status(&status));
    check_true("unknown queued record stays pending", status.queued_changes > 0);
    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_includes_v6_encrypted_records(void)
{
    char root[512];
    char private_key[5121];
    char collection[80];
    char record_id[180];
    char ciphertext[512];
    Habits habits;
    char *payload;
    int count;

    make_clean_root(root, sizeof(root), "sync-v6-encrypted-records");
    check_true("init v6 encrypted record db", storage_init(root));
    fill_test_private_key(private_key);
    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", private_key);
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habit_set_day_count(&habits, 0, 20260829, 3);
    habits_save(&habits);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("v6 protocol in sync payload",
               payload != NULL && strstr(payload, "\"protocol_version\":6") != NULL);
    check_true("inbe app id in sync payload",
               payload != NULL && strstr(payload, "\"app_id\":\"inbe\"") != NULL);
    check_true("v6 payload has no legacy data opt-in",
               payload != NULL && strstr(payload, "include_legacy_data") == NULL);
    check_true("v6 encrypted capabilities in sync payload",
               payload != NULL && strstr(payload, "\"client_capabilities\"") != NULL &&
                   strstr(payload, "v6-device-transactions") != NULL &&
                   strstr(payload, "encrypted-primary") != NULL &&
                   strstr(payload, "legacy-dual-write") == NULL);
    count = storage_json_array_count_path(payload, "$.encrypted_records");
    check_true("v6 encrypted records present", count > 0);
    check_true("first encrypted collection",
               storage_json_array_object_text(payload, "$.encrypted_records", 0,
                                              "collection", collection,
                                              sizeof(collection)) &&
                   collection[0] != '\0');
    check_true("first encrypted record id",
               storage_json_array_object_text(payload, "$.encrypted_records", 0,
                                              "id", record_id, sizeof(record_id)) &&
                   record_id[0] != '\0');
    check_true("first encrypted ciphertext",
               storage_json_array_object_text(payload, "$.encrypted_records", 0,
                                              "ciphertext", ciphertext,
                                              sizeof(ciphertext)) &&
                   ciphertext[0] != '\0' && strstr(ciphertext, "Yoga") == NULL);
    storage_free_sync_payload_json(payload);

    check_true("pre-v6 response rejected",
               !storage_apply_sync_response_json(
                   "{\"protocol_version\":4,\"status\":\"ok\","
                   "\"server_version\":10,\"changes\":{\"encrypted_records\":[]}}"));
    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("queued encrypted records survive rejected response",
               payload != NULL &&
                   storage_json_array_count_path(payload, "$.encrypted_records") > 0);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_ignores_plaintext_private_response(void)
{
    char root[512];
    const char *response =
        "{\"protocol_version\":6,\"status\":\"ok\","
        "\"server_version\":12,\"server_clock\":12,"
        "\"changes\":{\"habits\":[{\"id\":\"plaintext-habit\","
        "\"name\":\"Unexpected\",\"color_r\":1,\"color_g\":2,"
        "\"color_b\":3,\"sync_mode\":0,\"sync_activity\":0,"
        "\"counter_enabled\":0,\"sort_order\":0,\"deleted_at\":0,"
        "\"updated_at\":\"2026-08-29T12:30:00Z\"}],"
        "\"habit_days\":[],\"sessions\":[],\"encrypted_records\":[]}}";

    make_clean_root(root, sizeof(root), "sync-plaintext-ignored");
    check_true("init plaintext response db", storage_init(root));
    check_true("apply v6 response with plaintext private row",
               storage_apply_sync_response_json(response));
    check_int("plaintext private row ignored", storage_habit_count(), 0);
    check_int("plaintext row does not signal changed private data",
              storage_last_sync_changed(), 0);
    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_batches_large_outbox(void)
{
    char root[512];
    char db_path[512];
    sqlite3 *db = NULL;
    sqlite3_stmt *day_stmt = NULL;
    sqlite3_stmt *outbox_stmt = NULL;
    char *payload;
    const char *response =
        "{\"server_version\":1,\"server_clock\":1,\"changes\":{\"habits\":[],"
        "\"habit_days\":[],\"sessions\":[],\"meditation_logs\":[]}}";

    make_clean_root(root, sizeof(root), "sync-large-outbox-batch");
    check_true("init large outbox db", storage_init(root));
    storage_close();

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open large outbox raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        check_true("insert large outbox habit",
                   sqlite3_exec(db,
                                "INSERT INTO "
                                "habits(id,user_id,name,color_r,color_g,color_b,sync_mode,"
                                "sync_activity,counter_enabled,sort_order,deleted_at,updated_at) "
                                "VALUES('batch-habit',(SELECT id FROM users LIMIT 1),'Batch',"
                                "255,255,255,0,0,1,0,0,1781902800);",
                                NULL, NULL, NULL) == SQLITE_OK);
        check_true("prepare large outbox day inserts",
                   sqlite3_prepare_v2(db,
                                      "INSERT INTO habit_days(habit_id,local_date,completed,count,"
                                      "updated_at) "
                                      "VALUES('batch-habit',?1,1,1,1781902800)",
                                      -1, &day_stmt, NULL) == SQLITE_OK);
        check_true("prepare large outbox queue inserts",
                   sqlite3_prepare_v2(
                       db,
                       "INSERT INTO sync_outbox(entity_type,entity_id,local_date,queued_at) "
                       "VALUES('habit_day','batch-habit',?1,1781902800)",
                       -1, &outbox_stmt, NULL) == SQLITE_OK);
        if(day_stmt != NULL && outbox_stmt != NULL) {
            for(int i = 0; i < 405; i++) {
                sqlite3_bind_int(day_stmt, 1, 20260101 + i);
                check_true("insert large outbox day row", sqlite3_step(day_stmt) == SQLITE_DONE);
                sqlite3_reset(day_stmt);
                sqlite3_clear_bindings(day_stmt);
                sqlite3_bind_int(outbox_stmt, 1, 20260101 + i);
                check_true("insert large outbox queue row",
                           sqlite3_step(outbox_stmt) == SQLITE_DONE);
                sqlite3_reset(outbox_stmt);
                sqlite3_clear_bindings(outbox_stmt);
            }
        }
        if(day_stmt != NULL)
            sqlite3_finalize(day_stmt);
        if(outbox_stmt != NULL)
            sqlite3_finalize(outbox_stmt);
        sqlite3_close(db);
    }

    check_true("reopen large outbox db", storage_init(root));
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_int("large outbox payload is batched",
              storage_json_array_count_path(payload, "$.ops"), 400);
    storage_free_sync_payload_json(payload);
    check_true("apply large outbox batch response", storage_apply_sync_response_json(response));
    storage_close();
    check_int("large outbox leaves later rows queued",
              read_raw_count_query(root, "SELECT COUNT(*) FROM sync_outbox"), 6);

    remove_tree(root);
}

static void
test_sync_outbox_preserves_edits_after_snapshot(void)
{
    char root[512];
    Habits habits;
    char *payload;
    const char *empty_response = "{\"server_version\":1,\"changes\":{\"habits\":["
                                 "],\"habit_days\":[],\"sessions\":[]}}";

    make_clean_root(root, sizeof(root), "sync-outbox-snapshot");
    check_true("init outbox snapshot db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habit_set_day_count(&habits, 0, 20260618, 1);
    habits_save(&habits);

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("first queued edit in payload",
               payload != NULL && strstr(payload, "\"local_date\":20260618") != NULL);
    storage_free_sync_payload_json(payload);

    habit_set_day_count(&habits, 0, 20260619, 2);
    habits_save(&habits);
    check_true("apply response clears only snapshotted outbox",
               storage_apply_sync_response_json(empty_response));

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("later edit remains queued after snapshot clear",
               payload != NULL && strstr(payload, "\"local_date\":20260619") != NULL &&
                   strstr(payload, "\"count\":2") != NULL);
    check_true("earlier edit was cleared after snapshot success",
               payload != NULL && strstr(payload, "\"local_date\":20260618") == NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_apply_preserves_counter_counts(void)
{
    char root[512];
    const char *habit_id = "counter-habit";
    const char *lower_count_response =
        "{\"server_version\":1,\"changes\":{\"habits\":[],\"habit_days\":["
        "{\"habit_id\":\"counter-habit\",\"local_date\":20260619,"
        "\"completed\":true,\"count\":1,\"updated_at\":\"2026-06-19T21:00:00Z\"}"
        "],\"sessions\":[]}}";
    const char *higher_count_response =
        "{\"server_version\":2,\"changes\":{\"habits\":[],\"habit_days\":["
        "{\"habit_id\":\"counter-habit\",\"local_date\":20260619,"
        "\"completed\":true,\"count\":5,\"updated_at\":\"2026-06-19T21:00:00Z\"}"
        "],\"sessions\":[]}}";

    make_clean_root(root, sizeof(root), "sync-counter");
    check_true("init sync counter db", storage_init(root));
    storage_close();

    {
        char db_path[512];
        sqlite3 *db = NULL;
        make_path(db_path, sizeof(db_path), root, "inbe.db");
        check_true("open sync counter raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
        if(db != NULL) {
            check_true(
                "insert sync counter habit",
                sqlite3_exec(db,
                             "INSERT INTO "
                             "habits(id,user_id,name,color_r,color_g,color_b,sync_mode,sync_"
                             "activity,counter_enabled,sort_order,deleted_at,updated_at) "
                             "VALUES('counter-habit','default','Counter',255,255,255,0,0,1,0,"
                             "0,1781902800);"
                             "INSERT INTO "
                             "habit_days(habit_id,local_date,completed,count,updated_at) "
                             "VALUES('counter-habit',20260619,1,4,1781902800);",
                             NULL, NULL, NULL) == SQLITE_OK);
            sqlite3_close(db);
        }
    }

    check_true("reopen sync counter db", storage_init(root));
    check_true("apply lower equal counter", storage_apply_sync_response_json(lower_count_response));
    storage_close();
    check_int("lower equal sync applies latest server count",
              read_raw_habit_day_count(root, habit_id, 20260619), 1);

    check_true("reopen sync counter db for repair", storage_init(root));
    check_true("apply higher equal counter",
               storage_apply_sync_response_json(higher_count_response));
    storage_close();
    check_int("higher equal sync repairs counter",
              read_raw_habit_day_count(root, habit_id, 20260619), 5);

    remove_tree(root);
}

static void
test_sync_apply_clears_acknowledged_outbox_before_equal_timestamp_merge(void)
{
    char root[512];
    char db_path[512];
    sqlite3 *db = NULL;
    char *payload = NULL;
    const char *remote_response =
        "{\"server_version\":99,\"server_clock\":99,\"changes\":{\"habits\":[],"
        "\"habit_days\":[{\"habit_id\":\"push-ups\",\"local_date\":20260628,"
        "\"completed\":true,\"count\":1,\"updated_at\":\"2026-06-28T12:00:00Z\"}],"
        "\"sessions\":[],\"meditation_logs\":[]}}";

    make_clean_root(root, sizeof(root), "sync-outbox-equal-remote");
    check_true("init sync outbox equal db", storage_init(root));
    storage_close();

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open sync outbox equal raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        check_true(
            "insert sync outbox equal state",
            sqlite3_exec(db,
                         "INSERT INTO "
                         "habits(id,user_id,name,color_r,color_g,color_b,sync_mode,sync_activity,"
                         "counter_enabled,sort_order,deleted_at,updated_at) "
                         "VALUES('push-ups',(SELECT id FROM users LIMIT 1),'Push Ups',255,255,"
                         "255,0,0,0,0,0,1782648000);"
                         "INSERT INTO habit_days(habit_id,local_date,completed,count,updated_at) "
                         "VALUES('push-ups',20260628,0,0,1782648000);"
                         "INSERT INTO sync_outbox(entity_type,entity_id,local_date,queued_at) "
                         "VALUES('habit_day','push-ups',20260628,1782648000);",
                         NULL, NULL, NULL) == SQLITE_OK);
        sqlite3_close(db);
    }

    check_true("reopen sync outbox equal db", storage_init(root));
    storage_close();
    check_int("queued outbox before payload",
              read_raw_count_query(root, "SELECT COUNT(*) FROM sync_outbox"), 1);

    check_true("reopen sync outbox equal db for payload", storage_init(root));
    payload = storage_build_sync_payload_json(
        "55035d07339af4ea8e198413928073c2053c8d294ffd58bfa0c3094cf2ca496d", NULL);
    check_true("payload includes zero count habit day state",
               payload != NULL && strstr(payload, "\"habit_id\":\"push-ups\"") != NULL &&
                   strstr(payload, "\"completed\":false") != NULL &&
                   strstr(payload, "\"count\":0") != NULL &&
                   strstr(payload, "\"op_type\":\"upsert\"") != NULL);
    storage_free_sync_payload_json(payload);
    check_true("apply equal timestamp remote after ack",
               storage_apply_sync_response_json(remote_response));
    storage_close();

    check_int("equal timestamp remote applied after ack",
              read_raw_habit_day_count(root, "push-ups", 20260628), 1);
    check_int("acknowledged outbox cleared",
              read_raw_count_query(root, "SELECT COUNT(*) FROM sync_outbox"), 0);

    remove_tree(root);
}

static void
test_sync_apply_sessions_last_write_wins(void)
{
    char root[512];
    const char *session_id = "session-equal-time";
    const char *remote_response =
        "{\"server_version\":1,\"changes\":{\"habits\":[],\"habit_days\":[],"
        "\"sessions\":["
        "{\"id\":\"session-equal-time\",\"started_at\":\"2026-06-19T21:00:00Z\","
        "\"local_date\":20260619,\"topic\":\"0\",\"activity\":1,\"source\":"
        "\"remote\","
        "\"rounds_hash\":\"remote\",\"deleted_at\":0,\"updated_at\":\"2026-06-"
        "19T21:00:00Z\","
        "\"rounds\":[{\"round_index\":0,\"hold_seconds\":45}]}"
        "]}}";

    make_clean_root(root, sizeof(root), "sync-session-lww");
    check_true("init sync session db", storage_init(root));
    storage_close();

    {
        char db_path[512];
        sqlite3 *db = NULL;
        make_path(db_path, sizeof(db_path), root, "inbe.db");
        check_true("open sync session raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
        if(db != NULL) {
            check_true(
                "insert sync session",
                sqlite3_exec(db,
                             "INSERT INTO "
                             "sessions(id,user_id,started_at,local_date,topic,activity,source,"
                             "imported_at,rounds_hash,deleted_at,updated_at) "
                             "VALUES('session-equal-time','default',1781902800,20260619,0,1,'"
                             "local',1781902800,111,0,1781902800);"
                             "INSERT INTO session_rounds(session_id,round_index,seconds) "
                             "VALUES('session-equal-time',0,60);",
                             NULL, NULL, NULL) == SQLITE_OK);
            sqlite3_close(db);
        }
    }

    check_true("reopen sync session db", storage_init(root));
    check_true("apply equal session update", storage_apply_sync_response_json(remote_response));
    storage_close();
    check_int("equal session update replaces rounds",
              read_raw_session_round_seconds(root, session_id, 0), 45);

    {
        char db_path[512];
        sqlite3 *db = NULL;
        make_path(db_path, sizeof(db_path), root, "inbe.db");
        check_true("open queued sync session raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
        if(db != NULL) {
            check_true("reset queued sync session",
                       sqlite3_exec(db,
                                    "UPDATE sessions SET "
                                    "source='local',rounds_hash=111,updated_at=1781902800 WHERE "
                                    "id='session-equal-time';"
                                    "DELETE FROM session_rounds WHERE "
                                    "session_id='session-equal-time';"
                                    "INSERT INTO session_rounds(session_id,round_index,seconds) "
                                    "VALUES('session-equal-time',0,60);"
                                    "INSERT OR REPLACE INTO "
                                    "sync_outbox(entity_type,entity_id,local_date,queued_at) "
                                    "VALUES('session','session-equal-time',0,1781902800);",
                                    NULL, NULL, NULL) == SQLITE_OK);
            sqlite3_close(db);
        }
    }

    check_true("reopen queued sync session db", storage_init(root));
    check_true("apply equal queued session update",
               storage_apply_sync_response_json(remote_response));
    storage_close();
    check_int("equal queued session keeps local rounds",
              read_raw_session_round_seconds(root, session_id, 0), 60);

    remove_tree(root);
}

static void
test_sync_apply_updates_habit_counter_enabled(void)
{
    char root[512];
    Habits habits;
    const char *enabled_response =
        "{\"server_version\":1,\"changes\":{\"habits\":["
        "{\"id\":\"counter-toggle\",\"name\":\"Counter "
        "Toggle\",\"color_r\":10,\"color_g\":20,\"color_b\":30,"
        "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":1,\"sort_"
        "order\":0,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:00:00Z\"}"
        "],\"habit_days\":[],\"sessions\":[]}}";
    const char *disabled_response =
        "{\"server_version\":2,\"changes\":{\"habits\":["
        "{\"id\":\"counter-toggle\",\"name\":\"Counter "
        "Toggle\",\"color_r\":10,\"color_g\":20,\"color_b\":30,"
        "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":0,\"sort_"
        "order\":0,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:01:00Z\"}"
        "],\"habit_days\":[],\"sessions\":[]}}";

    make_clean_root(root, sizeof(root), "sync-counter-enabled");
    check_true("init sync counter enabled db", storage_init(root));
    check_true("apply counter enabled habit", storage_apply_sync_response_json(enabled_response));
    memset(&habits, 0, sizeof(habits));
    check_true("load enabled counter habit", storage_habits_load(&habits));
    check_int("remote enables multiple counts", habits.count, 1);
    check_int("counter enabled after remote enable", habits.items[0].counter_enabled, 1);

    check_true("apply counter disabled habit", storage_apply_sync_response_json(disabled_response));
    memset(&habits, 0, sizeof(habits));
    check_true("reload disabled counter habit", storage_habits_load(&habits));
    check_int("counter disabled after remote disable", habits.items[0].counter_enabled, 0);

    storage_close();
    remove_tree(root);
}

static void
test_stale_habit_save_keeps_synced_remote_habits(void)
{
    char root[512];
    Habits stale_habits;
    Habits loaded_habits;
    const char *remote_response =
        "{\"server_version\":1,\"changes\":{\"habits\":["
        "{\"id\":\"habit-2\",\"name\":\"Push "
        "ups\",\"color_r\":99,\"color_g\":196,\"color_b\":165,"
        "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":0,\"sort_"
        "order\":1,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:00:00Z\"},"
        "{\"id\":\"habit-3\",\"name\":\"Cold "
        "Shower\",\"color_r\":99,\"color_g\":196,\"color_b\":165,"
        "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":0,\"sort_"
        "order\":2,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:01:00Z\"}"
        "],\"habit_days\":["
        "{\"habit_id\":\"habit-2\",\"local_date\":20260619,\"completed\":true,"
        "\"count\":1,"
        "\"updated_at\":\"2026-06-19T21:00:00Z\"},"
        "{\"habit_id\":\"habit-3\",\"local_date\":20260619,\"completed\":true,"
        "\"count\":1,"
        "\"updated_at\":\"2026-06-19T21:01:00Z\"}"
        "],\"sessions\":[]}}";

    make_clean_root(root, sizeof(root), "sync-stale-habit-save");
    check_true("init stale habit save db", storage_init(root));
    memset(&stale_habits, 0, sizeof(stale_habits));
    habits_add_default_set(&stale_habits);

    check_true("apply remote habits behind stale UI",
               storage_apply_sync_response_json(remote_response));
    habits_save(&stale_habits);

    memset(&loaded_habits, 0, sizeof(loaded_habits));
    check_true("load habits after stale save", storage_habits_load(&loaded_habits));
    check_int("stale save keeps remote habit rows", loaded_habits.count, 4);
    check_true("remote push ups survived", find_habit_ci(&loaded_habits, "Push ups") != NULL);
    check_true("remote cold shower survived", find_habit_ci(&loaded_habits, "Cold Shower") != NULL);
    check_true("default yoga survived", find_habit_ci(&loaded_habits, "Yoga") != NULL);

    habits_free(&stale_habits);
    habits_free(&loaded_habits);
    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_resets_cursor_for_orphan_habit_days(void)
{
    char root[512];
    char db_path[512];
    char *payload;
    sqlite3 *db = NULL;

    make_clean_root(root, sizeof(root), "sync-orphan-habit-days");
    check_true("init orphan habit day db", storage_init(root));
    storage_close();
    insert_raw_habit_day(root, "habit-2", 20260617, 1);
    insert_raw_habit_day(root, "habit-3", 20260618, 1);

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open orphan cursor raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        check_true("set orphan sync cursor",
                   sqlite3_exec(db,
                                "INSERT OR REPLACE INTO meta(key,value) "
                                "VALUES('sync_last_server_version','530');"
                                "INSERT OR REPLACE INTO meta(key,value) "
                                "VALUES('sync_full_upload_done','1');"
                                "INSERT OR REPLACE INTO meta(key,value) "
                                "VALUES('sync_backfill_v2_done','1');",
                                NULL, NULL, NULL) == SQLITE_OK);
        sqlite3_close(db);
    }

    check_true("reopen orphan habit day db", storage_init(root));
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("orphan habit days request full snapshot",
               payload != NULL && strstr(payload, "\"since_server_version\":0") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_runs_one_time_habit_name_repair(void)
{
    char root[512];
    char db_path[512];
    char *payload;
    const char *empty_response =
        "{\"server_version\":530,\"changes\":{\"habits\":[],\"habit_days\":[],"
        "\"sessions\":[]}}";
    sqlite3 *db = NULL;

    make_clean_root(root, sizeof(root), "sync-habit-name-repair");
    check_true("init habit name repair db", storage_init(root));
    storage_close();

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open habit name repair raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        check_true("set old sync cursor", sqlite3_exec(db,
                                                       "INSERT OR REPLACE INTO meta(key,value) "
                                                       "VALUES('sync_last_server_version','530');"
                                                       "INSERT OR REPLACE INTO meta(key,value) "
                                                       "VALUES('sync_full_upload_done','1');"
                                                       "INSERT OR REPLACE INTO meta(key,value) "
                                                       "VALUES('sync_backfill_v2_done','1');",
                                                       NULL, NULL, NULL) == SQLITE_OK);
        sqlite3_close(db);
    }

    check_true("reopen habit name repair db", storage_init(root));
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("habit name repair requests full snapshot",
               payload != NULL && strstr(payload, "\"since_server_version\":0") != NULL);
    storage_free_sync_payload_json(payload);

    check_true("apply habit name repair response",
               storage_apply_sync_response_json(empty_response));
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("habit name repair only runs once",
               payload != NULL && strstr(payload, "\"since_server_version\":530") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_apply_merges_duplicate_habit_names(void)
{
    char root[512];
    Habits habits;
    Habit *merged;
    const char *response =
        "{\"server_version\":1,\"changes\":{\"habits\":["
        "{\"id\":\"habit-1\",\"name\":\"New "
        "Habit\",\"color_r\":99,\"color_g\":196,\"color_b\":165,"
        "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":0,\"sort_"
        "order\":0,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:00:00Z\"},"
        "{\"id\":\"habit-2\",\"name\":\"New "
        "Habit\",\"color_r\":99,\"color_g\":196,\"color_b\":165,"
        "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":0,\"sort_"
        "order\":1,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:01:00Z\"},"
        "{\"id\":\"meditation\",\"name\":\"Meditation\",\"color_r\":126,\"color_"
        "g\":183,\"color_b\":230,"
        "\"sync_mode\":1,\"sync_activity\":3,\"counter_enabled\":0,\"sort_"
        "order\":2,"
        "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:02:00Z\"}"
        "],\"habit_days\":["
        "{\"habit_id\":\"habit-1\",\"local_date\":20260617,\"completed\":true,"
        "\"count\":1,"
        "\"updated_at\":\"2026-06-19T21:00:00Z\"},"
        "{\"habit_id\":\"habit-2\",\"local_date\":20260618,\"completed\":true,"
        "\"count\":1,"
        "\"updated_at\":\"2026-06-19T21:01:00Z\"},"
        "{\"habit_id\":\"meditation\",\"local_date\":20260619,\"completed\":true,"
        "\"count\":1,"
        "\"updated_at\":\"2026-06-19T21:02:00Z\"}"
        "],\"sessions\":[]}}";

    make_clean_root(root, sizeof(root), "sync-duplicate-habit-names");
    check_true("init duplicate habit name db", storage_init(root));
    check_true("apply duplicate named habits", storage_apply_sync_response_json(response));
    memset(&habits, 0, sizeof(habits));
    check_true("load merged duplicate habits", storage_habits_load(&habits));
    check_int("duplicate habit names collapse to one tab", habits.count, 2);
    merged = find_habit_ci(&habits, "New Habit");
    check_true("merged habit visible", merged != NULL);
    if(merged != NULL) {
        check_true("first duplicate day kept", habit_completed_day(merged, 20260617));
        check_true("second duplicate day moved", habit_completed_day(merged, 20260618));
    }
    check_true("meditation remains visible", find_habit_ci(&habits, "Meditation") != NULL);

    habits_free(&habits);
    storage_close();
    remove_tree(root);
}

static void
test_sync_apply_preserves_queued_habit_counter_enabled(void)
{
    char root[512];
    char db_path[512];
    char sql[512];
    char response[1024];
    Habits habits;
    char habit_id[STORAGE_ID_SIZE];
    char *payload;
    sqlite3 *db = NULL;

    make_clean_root(root, sizeof(root), "sync-counter-enabled-queued");
    check_true("init queued counter enabled db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    snprintf(habit_id, sizeof(habit_id), "%s", habits.items[0].id);
    habits.items[0].counter_enabled = 1;
    habits_save(&habits);
    storage_close();

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open queued counter raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        snprintf(sql, sizeof(sql), "UPDATE habits SET updated_at=1781902800 WHERE id='%s';",
                 habit_id);
        check_true("pin queued counter updated_at",
                   sqlite3_exec(db, sql, NULL, NULL, NULL) == SQLITE_OK);
        sqlite3_close(db);
    }

    snprintf(response, sizeof(response),
             "{\"server_version\":1,\"changes\":{\"habits\":["
             "{\"id\":\"%s\",\"name\":\"Breathe\",\"color_r\":0,\"color_g\":0,"
             "\"color_b\":0,"
             "\"sync_mode\":0,\"sync_activity\":0,\"counter_enabled\":0,\"sort_"
             "order\":0,"
             "\"deleted_at\":0,\"updated_at\":\"2026-06-19T21:00:00Z\"}"
             "],\"habit_days\":[],\"sessions\":[]}}",
             habit_id);

    check_true("reopen queued counter enabled db", storage_init(root));
    check_true("apply stale equal counter enabled habit",
               storage_apply_sync_response_json(response));
    memset(&habits, 0, sizeof(habits));
    check_true("reload queued counter enabled habit", storage_habits_load(&habits));
    check_int("queued local counter enabled survives equal remote", habits.items[0].counter_enabled,
              1);

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("queued local counter enabled remains in payload",
               payload != NULL && strstr(payload, "\"counter_enabled\":1") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_session_linked_counts_materialize_for_sync(void)
{
    char root[512];
    char first_id[STORAGE_ID_SIZE + 4];
    char second_id[STORAGE_ID_SIZE + 4];
    int first_rounds[] = {30};
    int second_rounds[] = {45};
    int today = habits_today_index();
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "session-linked-count");
    check_true("init linked counter db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);

    check_true("save linked session one", storage_save_session_for_activity(
                                              first_rounds, 1, 0, 1, first_id, sizeof(first_id)));
    check_true(
        "save linked session two",
        storage_save_session_for_activity(second_rounds, 1, 0, 1, second_id, sizeof(second_id)));

    memset(&habits, 0, sizeof(habits));
    check_true("load linked counter habits", storage_habits_load(&habits));
    check_int("linked sessions materialize count", habit_day_count(&habits.items[0], today), 2);

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("linked session count is in sync payload",
               payload != NULL && strstr(payload, "\"count\":2") != NULL);
    storage_free_sync_payload_json(payload);

    habit_set_day_count(&habits, 0, today, 0);
    habits_save(&habits);
    memset(&habits, 0, sizeof(habits));
    check_true("reload linked counter after manual clear", storage_habits_load(&habits));
    check_int("manual clear overrides linked sessions", habit_day_count(&habits.items[0], today),
              0);
    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("manual clear is in sync payload",
               payload != NULL && strstr(payload, "\"completed\":false") != NULL &&
                   strstr(payload, "\"count\":0") != NULL);
    storage_free_sync_payload_json(payload);

    habit_set_day_count(&habits, 0, today, 2);
    habits_save(&habits);

    check_true("delete linked session one", storage_delete_session(first_id));
    memset(&habits, 0, sizeof(habits));
    check_true("reload linked counter after delete", storage_habits_load(&habits));
    check_int("linked session delete lowers derived count",
              habit_day_count(&habits.items[0], today), 1);

    habit_set_day_count(&habits, 0, today, 4);
    habits_save(&habits);
    check_true("delete linked session two", storage_delete_session(second_id));
    memset(&habits, 0, sizeof(habits));
    check_true("reload linked counter after manual override", storage_habits_load(&habits));
    check_int("linked session delete preserves manual count",
              habit_day_count(&habits.items[0], today), 4);

    storage_close();
    remove_tree(root);
}

static void
test_deleted_linked_session_clears_synced_habit_day(void)
{
    char root[512];
    char session_id[STORAGE_ID_SIZE + 4];
    int rounds[] = {60};
    int today = habits_today_index();
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "delete-linked-session-sync");
    check_true("init linked delete sync db", storage_init(root));
    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", "test-private-key");

    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habits_save(&habits);

    check_true("save linked synced session",
               storage_save_session_for_activity(rounds, 1, 0, 1, session_id,
                                                 sizeof(session_id)));
    memset(&habits, 0, sizeof(habits));
    check_true("load linked synced habit", storage_habits_load(&habits));
    check_int("linked synced session marks complete", habit_day_count(&habits.items[0], today), 1);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("initial linked habit day uploaded",
               payload != NULL && strstr(payload, "\"entity_type\":\"habit_day\"") != NULL &&
                   strstr(payload, "\"completed\":true") != NULL &&
                   strstr(payload, "\"count\":1") != NULL);
    storage_free_sync_payload_json(payload);
    check_true("apply upload marker before linked delete",
               storage_apply_sync_response_json(
                   "{\"server_version\":1,\"server_state_hash\":\"h1\","
                   "\"changes\":{\"habits\":[],\"habit_days\":[],\"sessions\":[],"
                   "\"meditation_logs\":[]}}"));

    check_true("delete last linked synced session", storage_delete_session(session_id));
    memset(&habits, 0, sizeof(habits));
    check_true("reload after linked synced delete", storage_habits_load(&habits));
    check_int("linked synced delete clears local habit", habit_day_count(&habits.items[0], today),
              0);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("linked session delete uploads session tombstone",
               payload != NULL && strstr(payload, "\"entity_type\":\"session\"") != NULL &&
                   strstr(payload, "\"deleted_at\":0") == NULL);
    check_true("linked session delete clears remote habit day",
               payload != NULL && strstr(payload, "\"entity_type\":\"habit_day\"") != NULL &&
                   strstr(payload, "\"completed\":false") != NULL &&
                   strstr(payload, "\"count\":0") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_deleted_linked_session_preserves_manual_habit_count(void)
{
    char root[512];
    char session_id[STORAGE_ID_SIZE + 4];
    int rounds[] = {60};
    int today = habits_today_index();
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "delete-linked-session-manual");
    check_true("init linked manual delete db", storage_init(root));
    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", "test-private-key");

    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habits_save(&habits);
    check_true("save linked manual session",
               storage_save_session_for_activity(rounds, 1, 0, 1, session_id,
                                                 sizeof(session_id)));
    memset(&habits, 0, sizeof(habits));
    check_true("load linked manual habit", storage_habits_load(&habits));
    habit_set_day_count(&habits, 0, today, 4);
    habits_save(&habits);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    storage_free_sync_payload_json(payload);
    check_true("apply upload marker before manual linked delete",
               storage_apply_sync_response_json(
                   "{\"server_version\":1,\"server_state_hash\":\"h1\","
                   "\"changes\":{\"habits\":[],\"habit_days\":[],\"sessions\":[],"
                   "\"meditation_logs\":[]}}"));

    check_true("delete linked session with manual count", storage_delete_session(session_id));
    memset(&habits, 0, sizeof(habits));
    check_true("reload manual linked delete habit", storage_habits_load(&habits));
    check_int("linked delete keeps manual habit count", habit_day_count(&habits.items[0], today),
              4);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("manual count is not cleared remotely",
               payload != NULL && strstr(payload, "\"completed\":false") == NULL &&
                   strstr(payload, "\"count\":0") == NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_existing_sessions_materialize_after_habit_save(void)
{
    char root[512];
    int rounds[] = {30};
    int today = habits_today_index();
    Habits habits;
    char *payload;

    make_clean_root(root, sizeof(root), "existing-session-linked-count");
    check_true("init existing linked counter db", storage_init(root));
    check_true("save existing linked session",
               storage_save_session_for_activity(rounds, 1, 0, 1, NULL, 0));

    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    memset(&habits, 0, sizeof(habits));
    check_true("load existing linked counter habits", storage_habits_load(&habits));
    check_int("existing linked session materializes after habit save",
              habit_day_count(&habits.items[0], today), 1);

    payload = storage_build_sync_payload_json("test-hash", "test-public-key");
    check_true("existing linked session count is in sync payload",
               payload != NULL && strstr(payload, "\"count\":1") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_sync_apply_meditation_logs_feed_profile_stats(void)
{
    char root[512];
    int streak = -1;
    long avg_hold = -1;

    make_clean_root(root, sizeof(root), "meditation-log-profile-stats");
    check_true("init meditation log profile db", storage_init(root));
    check_true("apply meditation log profile sync",
               storage_apply_sync_response_json(
                   "{\"server_version\":1,\"server_state_hash\":\"h1\","
                   "\"changes\":{\"habits\":[],\"habit_days\":[],"
                   "\"sessions\":[{\"id\":\"med-session-1\","
                   "\"started_at\":\"2026-07-15T00:00:00Z\","
                   "\"local_date\":20260715,\"topic\":0,\"activity\":1,"
                   "\"source\":\"sync\",\"rounds_hash\":101,\"deleted_at\":0,"
                   "\"updated_at\":\"2026-07-15T00:00:00Z\","
                   "\"rounds\":[{\"round_index\":0,\"hold_seconds\":600}]}],"
                   "\"meditation_logs\":["
                   "{\"id\":\"med-log-external\",\"session_id\":\"external-log-session\","
                   "\"duration_seconds\":1200,"
                   "\"completed_at\":\"2026-07-14T00:00:00Z\"},"
                   "{\"id\":\"med-log-duplicate\",\"session_id\":\"med-session-1\","
                   "\"duration_seconds\":3000,"
                   "\"completed_at\":\"2026-07-15T00:00:00Z\"}]}}"));
    check_true("meditation log profile stats call",
               storage_profile_activity_stats(1, 20260715, &streak, &avg_hold));
    check_int("meditation log profile streak", streak, 2);
    check_int("meditation log profile average", (int)avg_hold, 900);
    check_true("meditation log profile stale day call",
               storage_profile_activity_stats(1, 20260716, &streak, &avg_hold));
    check_int("meditation log profile stale day streak", streak, 0);
    storage_close();
    remove_tree(root);
}

static void
test_profile_week_stats_combines_habits_and_practices(void)
{
    char root[512];
    Habits habits;
    int rounds[] = {45};
    int active_days = -1;
    int practice_sessions = -1;

    make_clean_root(root, sizeof(root), "profile-week-stats");
    check_true("init profile week db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habits_save(&habits);

    check_true("save profile session today",
               storage_save_session_at_for_activity(20260715, 9, 0, 0,
                                                    rounds, 1, 0, 0, NULL, 0));
    check_true("save profile session earlier",
               storage_save_session_at_for_activity(20260713, 9, 0, 0,
                                                    rounds, 1, 0, 1, NULL, 0));
    check_true("save profile session outside week",
               storage_save_session_at_for_activity(20260708, 9, 0, 0,
                                                    rounds, 1, 0, 0, NULL, 0));
    check_true("save profile habit distinct day",
               storage_habit_day_save(habits.items[0].id, 20260714, 1, 1));
    check_true("save profile habit overlapping day",
               storage_habit_day_save(habits.items[0].id, 20260713, 1, 1));

    check_true("profile week stats call",
               storage_profile_week_stats(20260715, &active_days,
                                          &practice_sessions));
    check_int("profile week active days", active_days, 3);
    check_int("profile week practice sessions", practice_sessions, 2);

    storage_close();
    remove_tree(root);
}

static void
metadata_history_callback(const char *id, int year, int month, int day, int hour, int minute,
                          int second, int topic, int activity, const int *rounds, int round_count,
                          void *user)
{
    (void)id;
    (void)year;
    (void)month;
    (void)day;
    (void)hour;
    (void)minute;
    (void)second;
    (void)rounds;
    (void)round_count;
    (void)user;
    g_seen_topic = topic;
    g_seen_activity = activity;
}

static void
test_session_metadata(void)
{
    char root[512];
    int rounds[] = {30, 45};

    make_clean_root(root, sizeof(root), "metadata");
    check_true("init metadata db", storage_init(root));
    check_true("save metadata session",
               storage_save_session_for_activity(rounds, 2, 2, 3, NULL, 0));
    g_seen_topic = -1;
    g_seen_activity = -1;
    storage_list_session_records(metadata_history_callback, NULL);
    check_int("metadata topic", g_seen_topic, 2);
    check_int("metadata activity", g_seen_activity, 3);
    storage_close();
    remove_tree(root);
}

static void
assert_imported_database(const char *root)
{
    Habits habits;
    Habit *meditation;

    check_true("init imported db", storage_init(root));
    check_int("imported sessions", storage_session_count(), 1);
    memset(&habits, 0, sizeof(habits));
    check_true("imported habits load", storage_habits_load(&habits));
    check_int("imported habit count", habits.count, 2);
    meditation = find_habit_ci(&habits, "Meditation");
    check_true("imported meditation habit day",
               meditation != NULL && habit_completed_day(meditation, 20260613));
    check_true("imported yoga habit", find_habit_ci(&habits, "Yoga") != NULL);
    habits_free(&habits);
    storage_close();
}

static void
test_raw_db_import(void)
{
    char source[512], dest[512], db_path[512];

    make_clean_root(source, sizeof(source), "raw-source");
    make_clean_root(dest, sizeof(dest), "raw-dest");
    write_source_database(source);
    make_path(db_path, sizeof(db_path), source, "inbe.db");

    check_true("init raw import dest", storage_init(dest));
    check_true("raw db import", storage_import_zip(db_path));
    storage_close();
    assert_imported_database(dest);

    remove_tree(source);
    remove_tree(dest);
}

static void
test_zip_db_import(void)
{
    char source[512], dest[512], zip_path[512];

    make_clean_root(source, sizeof(source), "zip-source");
    make_clean_root(dest, sizeof(dest), "zip-dest");
    write_source_database(source);
    make_path(zip_path, sizeof(zip_path), source, "export.zip");

    check_true("init export source", storage_init(source));
    check_true("export zip", storage_export_zip(zip_path));
    storage_close();

    check_true("init zip import dest", storage_init(dest));
    check_true("zip db import", storage_import_zip(zip_path));
    storage_close();
    assert_imported_database(dest);

    remove_tree(source);
    remove_tree(dest);
}

static void
test_current_archive_entry_import(void)
{
    char source[512], dest[512], export_path[512], roundtrip_path[512];
    Archive exported = {0}, roundtrip = {0};
    void *database = NULL;
    size_t database_size = 0;

    make_clean_root(source, sizeof(source), "current-archive-source");
    make_clean_root(dest, sizeof(dest), "current-archive-dest");
    write_source_database(source);
    make_path(export_path, sizeof(export_path), source, "export.zip");
    make_path(roundtrip_path, sizeof(roundtrip_path), source, "current-inbe.zip");
    check_true("init current export source", storage_init(source));
    check_true("export database for current fixture", storage_export_zip(export_path));
    storage_close();

    check_true("open exported archive", ArchiveOpenZip(&exported, export_path));
    database = ArchiveReadNamedEntryHeap(&exported, STORAGE_EXPORT_ENTRY_DB,
                                         &database_size);
    check_true("read exported database", database != NULL && database_size > 0);
    ArchiveClose(&exported);
    check_true("create current Inbe archive", ArchiveCreateZip(&roundtrip, roundtrip_path));
    if(database != NULL) {
        check_true("write current Inbe database entry",
                   ArchiveAddMemory(&roundtrip, STORAGE_EXPORT_ENTRY_DB, database,
                                    database_size, ARCHIVE_DEFLATE));
    }
    check_true("finish current Inbe archive", ArchiveFinishZip(&roundtrip));
    ArchiveClose(&roundtrip);
    free(database);

    check_true("init current Inbe import destination", storage_init(dest));
    check_true("import current Inbe archive", storage_import_zip(roundtrip_path));
    storage_close();
    assert_imported_database(dest);
    remove_tree(source);
    remove_tree(dest);
}

static void
test_habit_name_merge_import(void)
{
    char source[512], dest[512], zip_path[512];
    Habits habits;
    Habit *habit;

    make_clean_root(source, sizeof(source), "habit-name-source");
    make_clean_root(dest, sizeof(dest), "habit-name-dest");
    make_path(zip_path, sizeof(zip_path), source, "export.zip");

    check_true("init habit merge source", storage_init(source));
    memset(&habits, 0, sizeof(habits));
    check_int("add imported meditation",
              habits_add_custom(&habits, "meditation", (Color){224, 124, 104, 255},
                                HABIT_SYNC_NONE, 0),
              0);
    habit_set_day(&habits, 0, 20260613, 1);
    habits_save(&habits);
    check_int("add imported push ups",
              habits_add_custom(&habits, "Push ups", (Color){180, 132, 220, 255},
                                HABIT_SYNC_NONE, 0),
              1);
    habit_set_day(&habits, 1, 20260614, 1);
    habits_save(&habits);
    check_int("add imported cold shower",
              habits_add_custom(&habits, "Cold Shower", (Color){99, 196, 165, 255},
                                HABIT_SYNC_NONE, 0),
              2);
    habit_set_day(&habits, 2, 20260615, 1);
    habits_save(&habits);
    check_true("habit merge export", storage_export_zip(zip_path));
    storage_close();

    check_true("init habit merge dest", storage_init(dest));
    memset(&habits, 0, sizeof(habits));
    habits_add_default_set(&habits);
    habit_set_day(&habits, 0, 20260612, 1);
    habits_save(&habits);
    check_true("habit merge import", storage_import_zip(zip_path));
    memset(&habits, 0, sizeof(habits));
    check_true("habit merge load", storage_habits_load(&habits));
    check_int("habit merge count", habits.count, 4);
    habit = find_habit_ci(&habits, "Meditation");
    check_true("habit merge meditation exists", habit != NULL);
    check_true("habit merge preserves local case",
               habit != NULL && strcmp(habit->name, "Meditation") == 0);
    check_true("habit merge keeps local day",
               habit != NULL && habit_completed_day(habit, 20260612));
    check_true("habit merge imports day", habit != NULL && habit_completed_day(habit, 20260613));
    habit = find_habit_ci(&habits, "Push ups");
    check_true("habit merge push ups exists", habit != NULL);
    check_true("habit merge push ups day", habit != NULL && habit_completed_day(habit, 20260614));
    habit = find_habit_ci(&habits, "Cold Shower");
    check_true("habit merge cold shower exists", habit != NULL);
    check_true("habit merge cold shower day",
               habit != NULL && habit_completed_day(habit, 20260615));
    storage_close();

    remove_tree(source);
    remove_tree(dest);
}

static void
test_import_conflict_prefers_data_over_empty(void)
{
    char source[512], dest[512], zip_path[512];
    Habits habits;
    Habit *habit;

    make_clean_root(source, sizeof(source), "conflict-source");
    make_clean_root(dest, sizeof(dest), "conflict-dest");
    make_path(zip_path, sizeof(zip_path), source, "conflict-export.zip");

    check_true("init conflict source", storage_init(source));
    memset(&habits, 0, sizeof(habits));
    check_int("add conflict source habit",
              habits_add_custom(&habits, "Meditation", (Color){224, 124, 104, 255},
                                HABIT_SYNC_NONE, 0),
              0);
    storage_set_setting_text("language", "");
    storage_close();
    insert_raw_habit_day(source, "habit-1", 20260618, 0);
    check_true("reopen conflict source", storage_init(source));
    check_true("conflict source export", storage_export_zip(zip_path));
    storage_close();

    check_true("init conflict dest", storage_init(dest));
    memset(&habits, 0, sizeof(habits));
    check_int("add conflict dest habit",
              habits_add_custom(&habits, "Meditation", (Color){126, 183, 230, 255},
                                HABIT_SYNC_NONE, 0),
              0);
    habit_set_day(&habits, 0, 20260618, 1);
    habits_save(&habits);
    storage_set_setting_text("language", "en");
    check_true("conflict import",
               storage_import_zip_ex(zip_path, STORAGE_IMPORT_DATA_AND_SETTINGS));
    memset(&habits, 0, sizeof(habits));
    check_true("conflict habits load", storage_habits_load(&habits));
    habit = find_habit_ci(&habits, "Meditation");
    check_true("conflict keeps completed day",
               habit != NULL && habit_completed_day(habit, 20260618));
    check_str("conflict keeps non-empty setting", storage_get_setting_text("language"), "en");
    storage_close();

    remove_tree(source);
    remove_tree(dest);
}

static void
test_delete_all_resets_habits_to_empty_storage(void)
{
    char root[512];
    Habits habits;
    long long deleted;

    make_clean_root(root, sizeof(root), "delete-all");
    check_true("init delete all db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    check_int(
        "add delete all habit",
        habits_add_custom(&habits, "Work out", (Color){99, 196, 165, 255}, HABIT_SYNC_NONE, 0),
        0);
    habit_set_day(&habits, 0, 20260618, 1);
    habits_save(&habits);
    check_int("delete all habit count before", storage_habit_count(), 1);
    check_true("delete all sees habit-only data", storage_has_any());

    deleted = storage_delete_all_sessions();
    check_true("delete all removed habit data", deleted >= 2);
    check_int("delete all habit count after", storage_habit_count(), 0);
    check_true("delete all hides active data", !storage_has_any());

    habits_add_default_set(&habits);
    memset(&habits, 0, sizeof(habits));
    check_true("load default habit after delete all", storage_habits_load(&habits));
    check_int("default habit count after delete all", habits.count, 2);
    check_true("default meditation after delete all", find_habit_ci(&habits, "Meditation") != NULL);
    check_true("default yoga after delete all", find_habit_ci(&habits, "Yoga") != NULL);
    check_true("old workout day removed",
               !habit_completed_day(find_habit_ci(&habits, "Meditation"), 20260618));
    storage_close();

    remove_tree(root);
}

static void
test_delete_all_without_sync_account_does_not_queue_remote_deletes(void)
{
    char root[512];
    Habits habits;
    char *payload;
    long long deleted;

    make_clean_root(root, sizeof(root), "delete-all-no-sync-account");
    check_true("init local reset db", storage_init(root));
    storage_set_setting_text("sync_public_id", "");
    storage_set_setting_text("sync_public_key", "");
    storage_set_setting_text("sync_private_key", "");

    memset(&habits, 0, sizeof(habits));
    check_int(
        "add local reset habit",
        habits_add_custom(&habits, "Work out", (Color){99, 196, 165, 255}, HABIT_SYNC_NONE, 0),
        0);
    habit_set_day(&habits, 0, 20260618, 1);
    habits_save(&habits);

    deleted = storage_delete_all_sessions();
    check_true("local reset deleted rows", deleted >= 2);
    check_int("local reset active habit count", storage_habit_count(), 0);

    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", "test-private-key");
    storage_reset_sync_state();
    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("fresh imported account sends bootstrap",
               payload != NULL && strstr(payload, "\"since_server_version\":0") != NULL &&
                   strstr(payload, "\"bootstrap\":true") != NULL);
    check_true("fresh imported account has no stale habit tombstones",
               payload != NULL && strstr(payload, "\"habits\":[]") != NULL);
    check_true("fresh imported account has no stale habit day clears",
               payload != NULL && strstr(payload, "\"habit_days\":[]") != NULL);
    check_true("fresh imported account has no stale session tombstones",
               payload != NULL && strstr(payload, "\"sessions\":[]") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_deleted_habit_payload_clears_remote_days(void)
{
    char root[512];
    Habits habits;
    char deleted_id[STORAGE_ID_SIZE];
    char *payload;

    make_clean_root(root, sizeof(root), "deleted-habit-payload");
    check_true("init deleted habit payload db", storage_init(root));
    storage_set_setting_text("sync_public_id", "test-public-id");
    storage_set_setting_text("sync_public_key", "test-public-key");
    storage_set_setting_text("sync_private_key", "test-private-key");

    memset(&habits, 0, sizeof(habits));
    check_int("add deleted payload habit",
              habits_add_custom(&habits, "Cold shower", (Color){99, 196, 165, 255},
                                HABIT_SYNC_NONE, 0),
              0);
    habit_set_day_count(&habits, 0, 20260618, 3);
    habits_save(&habits);
    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    storage_free_sync_payload_json(payload);
    check_true("apply upload marker before delete",
               storage_apply_sync_response_json(
                   "{\"server_version\":1,\"server_state_hash\":\"h1\","
                   "\"changes\":{\"habits\":[],\"habit_days\":[],\"sessions\":[],"
                   "\"meditation_logs\":[]}}"));

    memset(&habits, 0, sizeof(habits));
    check_true("reload deleted payload habit", storage_habits_load(&habits));
    snprintf(deleted_id, sizeof(deleted_id), "%s", habits.items[0].id);
    habits_delete(&habits, 0);
    habits_save(&habits);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("deleted habit payload includes tombstone",
               payload != NULL && strstr(payload, deleted_id) != NULL &&
                   strstr(payload, "\"deleted_at\":0") == NULL);
    check_true("deleted habit payload clears habit day",
               payload != NULL && strstr(payload, "\"entity_type\":\"habit_day\"") != NULL &&
                   strstr(payload, "\"completed\":false") != NULL &&
                   strstr(payload, "\"count\":0") != NULL);
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_empty_initialized_habits_seed_meditation_on_startup(void)
{
    char root[512];
    char db_path[512];
    sqlite3 *db = NULL;
    Habits habits;

    make_clean_root(root, sizeof(root), "empty-initialized-habits");
    check_true("init empty initialized habit db", storage_init(root));
    storage_mark_habits_initialized();
    storage_close();

    make_path(db_path, sizeof(db_path), root, "inbe.db");
    check_true("open empty initialized raw db", sqlite3_open(db_path, &db) == SQLITE_OK);
    if(db != NULL) {
        check_true("clear empty initialized habits",
                   sqlite3_exec(db, "DELETE FROM habit_days; DELETE FROM habits;", NULL, NULL,
                                NULL) == SQLITE_OK);
        sqlite3_close(db);
    }

    check_true("reopen empty initialized habit db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    habits_init(&habits);
    check_int("empty initialized startup seeds default habits", habits.count, 2);
    check_true("empty initialized startup seeds meditation",
               find_habit_ci(&habits, "Meditation") != NULL);
    check_true("empty initialized startup seeds yoga", find_habit_ci(&habits, "Yoga") != NULL);
    check_int("empty initialized meditation linked mode",
              find_habit_ci(&habits, "Meditation") != NULL
                  ? find_habit_ci(&habits, "Meditation")->sync_mode
                  : -1,
              HABIT_SYNC_ACTIVITIES);
    check_int("empty initialized meditation linked activities",
              find_habit_ci(&habits, "Meditation") != NULL
                  ? find_habit_ci(&habits, "Meditation")->sync_activity
                  : -1,
              (1 << 0) | (1 << 1) | (1 << 3));
    check_int("empty initialized yoga linked mode",
              find_habit_ci(&habits, "Yoga") != NULL ? find_habit_ci(&habits, "Yoga")->sync_mode
                                                     : -1,
              HABIT_SYNC_ACTIVITIES);
    check_int("empty initialized yoga linked activities",
              find_habit_ci(&habits, "Yoga") != NULL ? find_habit_ci(&habits, "Yoga")->sync_activity
                                                     : -1,
              (1 << 2));
    habits_free(&habits);

    memset(&habits, 0, sizeof(habits));
    check_true("load seeded defaults from storage", storage_habits_load(&habits));
    check_int("seeded defaults persisted", habits.count, 2);
    check_true("persisted seeded meditation", find_habit_ci(&habits, "Meditation") != NULL);
    check_true("persisted seeded yoga", find_habit_ci(&habits, "Yoga") != NULL);
    check_int("persisted meditation linked mode",
              find_habit_ci(&habits, "Meditation") != NULL
                  ? find_habit_ci(&habits, "Meditation")->sync_mode
                  : -1,
              HABIT_SYNC_ACTIVITIES);
    check_int("persisted meditation linked activities",
              find_habit_ci(&habits, "Meditation") != NULL
                  ? find_habit_ci(&habits, "Meditation")->sync_activity
                  : -1,
              (1 << 0) | (1 << 1) | (1 << 3));

    habits_free(&habits);
    storage_close();
    remove_tree(root);
}

static void
test_default_habits_can_wait_for_language_setup(void)
{
    char root[512];
    Habits habits;

    make_clean_root(root, sizeof(root), "deferred-default-habits");
    check_true("init deferred default habit db", storage_init(root));

    memset(&habits, 0, sizeof(habits));
    habits_init_with_defaults(&habits, 0);
    check_int("deferred startup keeps habits empty", habits.count, 0);
    check_int("deferred startup does not initialize habits",
              storage_habits_initialized(), 0);
    habits_free(&habits);

    memset(&habits, 0, sizeof(habits));
    check_true("seed defaults after language setup",
               habits_seed_default_set_if_needed(&habits));
    check_int("deferred defaults seeded", habits.count, 2);
    check_true("deferred meditation exists", find_habit_ci(&habits, "Meditation") != NULL);
    check_true("deferred yoga exists", find_habit_ci(&habits, "Yoga") != NULL);
    check_int("deferred habits initialized", storage_habits_initialized(), 1);
    habits_free(&habits);

    memset(&habits, 0, sizeof(habits));
    check_true("load deferred seeded defaults", storage_habits_load(&habits));
    check_int("deferred persisted count", habits.count, 2);
    habits_free(&habits);
    storage_close();
    remove_tree(root);
}

static void
test_existing_default_meditation_is_not_repaired_on_startup(void)
{
    char root[512];
    Habits habits;
    Habit *meditation;

    make_clean_root(root, sizeof(root), "default-meditation-no-repair");
    check_true("init default meditation no repair db", storage_init(root));
    memset(&habits, 0, sizeof(habits));
    check_int("add unlinked default meditation",
              habits_add_custom(&habits, "Meditation", (Color){126, 183, 230, 255},
                                HABIT_SYNC_NONE, 0),
              0);
    habits_free(&habits);

    memset(&habits, 0, sizeof(habits));
    habits_init(&habits);
    check_int("default meditation no repair count", habits.count, 1);
    meditation = find_habit_ci(&habits, "Meditation");
    check_true("default meditation no repair exists", meditation != NULL);
    check_int("default meditation no repair sync mode",
              meditation != NULL ? meditation->sync_mode : -1, HABIT_SYNC_NONE);
    check_int("default meditation no repair sync activity",
              meditation != NULL ? meditation->sync_activity : -1, 0);
    habits_free(&habits);

    memset(&habits, 0, sizeof(habits));
    check_true("load unchanged default meditation", storage_habits_load(&habits));
    meditation = find_habit_ci(&habits, "Meditation");
    check_int("persisted unchanged sync mode", meditation != NULL ? meditation->sync_mode : -1,
              HABIT_SYNC_NONE);
    check_int("persisted unchanged sync activity",
              meditation != NULL ? meditation->sync_activity : -1, 0);
    habits_free(&habits);
    storage_close();
    remove_tree(root);
}

static void
write_multi_habit_source_database(const char *root, const char *zip_path)
{
    int rounds[] = {77};
    Habits habits;

    check_true("init multi habit source", storage_init(root));
    check_true("save multi habit source session",
               storage_save_session_for_activity(rounds, 1, 0, 1, NULL, 0));
    memset(&habits, 0, sizeof(habits));
    check_int("add meditation habit",
              habits_add_custom(&habits, "Meditation", (Color){224, 124, 104, 255},
                                HABIT_SYNC_ACTIVITIES, (1 << 0) | (1 << 1)),
              0);
    check_int("add push ups habit",
              habits_add_custom(&habits, "Push ups", (Color){180, 132, 220, 255},
                                HABIT_SYNC_NONE, 0),
              1);
    check_int("add cold shower habit",
              habits_add_custom(&habits, "Cold Shower", (Color){99, 196, 165, 255},
                                HABIT_SYNC_NONE, 0),
              2);
    habit_set_day(&habits, 0, 20260617, 1);
    habits_save(&habits);
    habit_set_day(&habits, 1, 20260617, 1);
    habits_save(&habits);
    habit_set_day(&habits, 2, 20260617, 1);
    habits_save(&habits);
    storage_set_setting_int("speed", 7);
    storage_set_setting_int("sun_salutation_repetitions", 6);
    storage_set_setting_int("sun_salutation_start_seconds", 9);
    storage_set_setting_int("sun_salutation_end_seconds", 4);
    storage_set_setting_int("sun_salutation_figure", 1);
    storage_set_setting_int("audio_custom_music_count", 1);
    storage_set_setting_text("audio_custom_music_0_title", "Test track");
    storage_set_setting_text("audio_custom_music_0_path", "/tmp/test-track.ogg");
    storage_set_setting_text("audio_custom_music_0_file", "ignore-me");
    storage_set_setting_text("language", "en");
    storage_set_setting_text("future_unknown_key", "ignore-me");
    check_true("export multi habit source", storage_export_zip(zip_path));
    storage_close();
}

static void
assert_multi_habits_imported(const char *root, int want_speed, int expect_settings)
{
    Habits habits;
    Habit *habit;

    check_true("init multi habit import db", storage_init(root));
    check_int("multi habit imported sessions", storage_session_count(), 1);
    memset(&habits, 0, sizeof(habits));
    check_true("multi habit load", storage_habits_load(&habits));
    check_int("multi habit count", habits.count, 3);
    habit = find_habit_ci(&habits, "Meditation");
    check_true("multi meditation exists", habit != NULL);
    check_int("multi meditation sync mode", habit != NULL ? habit->sync_mode : -1,
              HABIT_SYNC_ACTIVITIES);
    check_int("multi meditation sync activity", habit != NULL ? habit->sync_activity : -1,
              (1 << 0) | (1 << 1));
    check_true("multi meditation day", habit != NULL && habit_completed_day(habit, 20260617));
    habit = find_habit_ci(&habits, "Push ups");
    check_true("multi push ups day", habit != NULL && habit_completed_day(habit, 20260617));
    habit = find_habit_ci(&habits, "Cold Shower");
    check_true("multi cold shower day", habit != NULL && habit_completed_day(habit, 20260617));
    check_int("multi import speed setting", storage_get_setting_int("speed", -1), want_speed);
    if(expect_settings) {
        check_int("multi import sun reps setting",
                  storage_get_setting_int("sun_salutation_repetitions", -1), 6);
        check_int("multi import sun start setting",
                  storage_get_setting_int("sun_salutation_start_seconds", -1), 9);
        check_int("multi import sun end setting",
                  storage_get_setting_int("sun_salutation_end_seconds", -1), 4);
        check_int("multi import sun figure setting",
                  storage_get_setting_int("sun_salutation_figure", -1), 1);
        check_int("multi import audio count",
                  storage_get_setting_int("audio_custom_music_count", -1), 1);
        check_str("multi import audio title",
                  storage_get_setting_text("audio_custom_music_0_title"),
                  "Test track");
        check_str("multi import audio path",
                  storage_get_setting_text("audio_custom_music_0_path"),
                  "/tmp/test-track.ogg");
    } else {
        check_int("multi data-only skips sun figure",
                  storage_get_setting_int("sun_salutation_figure", -1), -1);
        check_int("multi data-only skips audio count",
                  storage_get_setting_int("audio_custom_music_count", -1), -1);
    }
    check_str("multi import malformed audio setting",
              storage_get_setting_text("audio_custom_music_0_file"), NULL);
    check_str("multi import unknown setting", storage_get_setting_text("future_unknown_key"), NULL);
    storage_close();
}

static void
test_import_modes_preserve_habits_and_settings_choice(void)
{
    char source[512], dest_data[512], dest_settings[512], zip_path[512];
    StorageImportInfo info;

    make_clean_root(source, sizeof(source), "multi-source");
    make_clean_root(dest_data, sizeof(dest_data), "multi-dest-data");
    make_clean_root(dest_settings, sizeof(dest_settings), "multi-dest-settings");
    make_path(zip_path, sizeof(zip_path), source, "multi-export.zip");
    write_multi_habit_source_database(source, zip_path);

    check_true("init inspect dest", storage_init(dest_data));
    memset(&info, 0, sizeof(info));
    check_true("inspect multi export", storage_inspect_import(zip_path, &info));
    check_true("inspect valid", info.valid);
    check_true("inspect sessions", info.has_sessions);
    check_true("inspect habits", info.has_habits);
    check_true("inspect settings", info.has_settings);
    check_int("inspect habit count", info.habit_count, 3);
    storage_set_setting_int("speed", 1);
    check_true("multi data only import",
               storage_import_zip_ex(zip_path, STORAGE_IMPORT_DATA_ONLY));
    storage_close();
    assert_multi_habits_imported(dest_data, 1, 0);

    check_true("init settings import dest", storage_init(dest_settings));
    storage_set_setting_int("speed", 1);
    check_true("multi data settings import",
               storage_import_zip_ex(zip_path, STORAGE_IMPORT_DATA_AND_SETTINGS));
    storage_close();
    assert_multi_habits_imported(dest_settings, 7, 1);

    remove_tree(source);
    remove_tree(dest_data);
    remove_tree(dest_settings);
}

static void
write_unsupported_file_session_zip(const char *path, const char *prefix)
{
    Archive archive;
    char archive_name[256];
    const char rounds[] = "31\n35\n39\n27\n";

    memset(&archive, 0, sizeof(archive));
    snprintf(archive_name, sizeof(archive_name), "%s/sessions/2026/06/13/breathing-010203", prefix);
    check_true("create legacy zip", ArchiveCreateZip(&archive, path));
    check_true("add legacy metadata",
               ArchiveAddMemory(&archive, "lotus-data/metadata.txt", "Legacy BreathSession export\n",
                                19, ARCHIVE_STORE));
    check_true("add legacy session",
               ArchiveAddMemory(&archive, archive_name, rounds, sizeof(rounds) - 1,
                                ARCHIVE_DEFLATE));
    check_true("finalize legacy zip", ArchiveFinishZip(&archive));
    ArchiveClose(&archive);
}

static void
test_unsupported_file_session_zip(void)
{
    char source[512], dest[512], zip_path[512];
    StorageImportInfo info;

    make_clean_root(source, sizeof(source), "legacy-source");
    make_clean_root(dest, sizeof(dest), "legacy-dest");
    make_path(zip_path, sizeof(zip_path), source, "legacy.zip");
    write_unsupported_file_session_zip(zip_path, "custom-root");

    check_true("init legacy import dest", storage_init(dest));
    memset(&info, 0, sizeof(info));
    check_true("unsupported file-session zip inspection rejected",
               !storage_inspect_import(zip_path, &info));
    check_true("unsupported file-session zip stays invalid", !info.valid);
    check_true("unsupported file-session zip rejected", !storage_import_zip(zip_path));
    check_int("unsupported zip imports no sessions", storage_session_count(), 0);
    storage_close();

    remove_tree(source);
    remove_tree(dest);
}

static void
write_text_file(const char *path, const char *text)
{
    FILE *fp = fopen(path, "wb");

    check_true("open text file", fp != NULL);
    if(fp == NULL)
        return;
    check_true("write text file", fwrite(text, 1, strlen(text), fp) == strlen(text));
    fclose(fp);
}

static void
test_deleted_list_defaults_stay_deleted(void)
{
    char root[512];
    EListState state = {0};
    make_clean_root(root, sizeof(root), "elist-defaults-once");
    check_true("init list defaults db", storage_init(root));
    check_true("load initial lists", storage_elist_load(&state));
    check_int("initial list count", state.list_count, 1);
    check_int("initial task count", state.item_count, 3);
    for(int i = 0; i < state.item_count; i++)
        check_true("delete starter task", storage_elist_delete_item(state.items[i].id));
    check_true("reload empty list", storage_elist_load(&state));
    check_int("deleted tasks stay deleted", state.item_count, 0);
    check_true("delete last list", storage_elist_delete_list(state.lists[0].id));
    /* Simulate an existing installation predating the initialization marker. */
    storage_set_setting_int("elist_initialized", 0);
    storage_close();
    check_true("reopen empty lists db", storage_init(root));
    check_true("reload deleted lists", storage_elist_load(&state));
    check_int("deleted lists stay deleted after restart", state.list_count, 0);
    check_int("deleted tasks stay deleted after restart", state.item_count, 0);
    storage_close();
}

static void
test_onelist_import_and_sync_collections(void)
{
    char root[512];
    char path[512];
    char private_key[5121];
    EListState state;
    char *payload;

    make_clean_root(root, sizeof(root), "onelist-import");
    make_path(path, sizeof(path), root, "tasks.1list");
    write_text_file(path,
                    "{\"title\":\"Inbox\",\"items\":["
                    "{\"title\":\"Open\",\"comment\":\"Details\",\"done\":false,\"id\":1},"
                    "{\"title\":\"Finished\",\"comment\":\"\",\"done\":true,\"id\":2}]}");
    check_true("init OneList import db", storage_init(root));
    fill_test_private_key(private_key);
    storage_set_setting_text("sync_private_key", private_key);
    check_true("import OneList file", storage_elist_import_onelist(path));
    memset(&state, 0, sizeof(state));
    check_true("load imported EList", storage_elist_load(&state));
    check_int("imported EList list count", state.list_count, 1);
    check_int("imported EList item count", state.item_count, 2);
    check_str("imported EList title", state.lists[0].title, "Inbox");
    check_str("imported EList comment", state.items[0].comment, "Details");
    check_int("imported EList done", state.items[1].done, 1);

    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("EList list Daochi collection",
               payload != NULL &&
                   strstr(payload, "private.inbe.v1.elist-lists") != NULL);
    check_true("EList item Daochi collection",
               payload != NULL &&
                   strstr(payload, "private.inbe.v1.elist-items") != NULL);
    storage_free_sync_payload_json(payload);
    storage_close();
    remove_tree(root);
}

static void
test_historical_file_session_startup(void)
{
    char root[512];
    char session_path[512];

    make_clean_root(root, sizeof(root), "legacy-files");
    make_nested_dir(root, "2026", "06", "13");
    make_path(session_path, sizeof(session_path), root, "2026/06/13/breathing-010203");
    write_text_file(session_path, "31\n35\n39\n27\n");

    check_true("init with historical file sessions", storage_init(root));
    check_int("historical session imported", storage_session_count(), 1);
    check_true("historical source file retained", FileExists(session_path));
    storage_close();

    check_true("reopen after file import", storage_init(root));
    check_int("historical session not duplicated", storage_session_count(), 1);
    storage_close();
    remove_tree(root);
}

static void
write_tickmate_database(const char *path)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    char *error = NULL;

    check_true("open tickmate db", sqlite3_open(path, &db) == SQLITE_OK);
    if(db == NULL)
        return;
    check_true("create tickmate db",
               sqlite3_exec(db,
                            "CREATE TABLE tracks(_id integer primary key autoincrement,"
                            "name text not null,description text not null,icon text not null,"
                            "enabled integer not null,multiple_entries_per_day integer DEFAULT 0,"
                            "color integer DEFAULT 0,\"order\" integer DEFAULT -1);"
                            "CREATE TABLE ticks(_id integer primary key autoincrement,"
                            "_track_id integer,year integer,month integer,day integer,"
                            "hour integer,minute integer,second integer,has_time_info integer "
                            "DEFAULT 0);"
                            "INSERT INTO "
                            "tracks(_id,name,description,icon,enabled,multiple_entries_per_day,"
                            "color,\"order\") "
                            "VALUES(1,'Meditation','Silenced my mind','',1,1,8925,0);"
                            "INSERT INTO "
                            "ticks(_track_id,year,month,day,hour,minute,second,has_time_info) "
                            "VALUES(1,2026,0,1,0,0,0,0),"
                            "(1,2026,1,2,0,0,0,0),"
                            "(1,2026,2,3,0,0,0,0),"
                            "(1,2026,3,4,0,0,0,0),"
                            "(1,2026,4,5,0,0,0,0),"
                            "(1,2026,5,6,0,0,0,0),"
                            "(1,2026,6,7,0,0,0,0),"
                            "(1,2026,7,8,0,0,0,0),"
                            "(1,2026,8,9,0,0,0,0),"
                            "(1,2026,9,10,0,0,0,0),"
                            "(1,2026,10,11,0,0,0,0),"
                            "(1,2026,11,12,0,0,0,0),"
                            "(1,2025,0,1,0,0,0,0),"
                            "(1,2025,0,1,0,0,0,0);",
                            NULL, NULL, &error) == SQLITE_OK);
    if(error != NULL) {
        fprintf(stderr, "tickmate setup SQL error: %s\n", error);
        sqlite3_free(error);
    }
    check_true(
        "prepare large tickmate insert",
        sqlite3_prepare_v2(db,
                           "INSERT INTO "
                           "ticks(_track_id,year,month,day,hour,minute,second,has_time_info) "
                           "VALUES(1,?1,?2,?3,0,0,0,0)",
                           -1, &stmt, NULL) == SQLITE_OK);
    if(stmt != NULL) {
        struct tm day;

        check_true("begin large tickmate insert",
                   sqlite3_exec(db, "BEGIN", NULL, NULL, NULL) == SQLITE_OK);
        memset(&day, 0, sizeof(day));
        day.tm_year = 2025 - 1900;
        day.tm_mon = 0;
        day.tm_mday = 1;
        day.tm_hour = 12;
        mktime(&day);
        for(int i = 0; i < 12000; i++) {
            sqlite3_reset(stmt);
            sqlite3_clear_bindings(stmt);
            sqlite3_bind_int(stmt, 1, day.tm_year + 1900);
            sqlite3_bind_int(stmt, 2, day.tm_mon);
            sqlite3_bind_int(stmt, 3, day.tm_mday);
            check_true("large tickmate insert row", sqlite3_step(stmt) == SQLITE_DONE);
            day.tm_mday++;
            mktime(&day);
        }
        check_true("commit large tickmate insert",
                   sqlite3_exec(db, "COMMIT", NULL, NULL, NULL) == SQLITE_OK);
        sqlite3_finalize(stmt);
    }
    sqlite3_close(db);
}

static void
test_tickmate_db_import(void)
{
    char source[512], dest[512], db_path[512];
    Habits habits;

    make_clean_root(source, sizeof(source), "tickmate-source");
    make_clean_root(dest, sizeof(dest), "tickmate-dest");
    make_path(db_path, sizeof(db_path), source, "tickmate.db");
    write_tickmate_database(db_path);

    check_true("init tickmate import dest", storage_init(dest));
    check_true("tickmate db import", storage_import_zip(db_path));
    memset(&habits, 0, sizeof(habits));
    check_true("tickmate habits load", storage_habits_load(&habits));
    check_int("tickmate habit count", habits.count, 1);
    check_true("tickmate january day", habit_completed_day(&habits.items[0], 20260101));
    check_true("tickmate february day", habit_completed_day(&habits.items[0], 20260202));
    check_true("tickmate march day", habit_completed_day(&habits.items[0], 20260303));
    check_true("tickmate april day", habit_completed_day(&habits.items[0], 20260404));
    check_true("tickmate may day", habit_completed_day(&habits.items[0], 20260505));
    check_true("tickmate june day", habit_completed_day(&habits.items[0], 20260606));
    check_true("tickmate july day", habit_completed_day(&habits.items[0], 20260707));
    check_true("tickmate august day", habit_completed_day(&habits.items[0], 20260808));
    check_true("tickmate september day", habit_completed_day(&habits.items[0], 20260909));
    check_true("tickmate october day", habit_completed_day(&habits.items[0], 20261010));
    check_true("tickmate november day", habit_completed_day(&habits.items[0], 20261111));
    check_true("tickmate december day", habit_completed_day(&habits.items[0], 20261212));
    check_true("tickmate loads thousands of days", habit_completed_day(&habits.items[0], 20571108));
    check_true("tickmate habit name", strcmp(habits.items[0].name, "Meditation") == 0);
    check_int("tickmate enables counter habit", habits.items[0].counter_enabled, 1);
    check_int("tickmate imports count", habit_day_count(&habits.items[0], 20250101), 3);
    storage_close();

    remove_tree(source);
    remove_tree(dest);
}

static void
test_tickmate_reimport_recovers_counter_data(void)
{
    char source[512], dest[512], db_path[512];
    Habits habits;

    make_clean_root(source, sizeof(source), "tickmate-reimport-source");
    make_clean_root(dest, sizeof(dest), "tickmate-reimport-dest");
    make_path(db_path, sizeof(db_path), source, "tickmate.db");
    write_tickmate_database(db_path);

    check_true("init tickmate reimport dest", storage_init(dest));
    memset(&habits, 0, sizeof(habits));
    check_int("add old boolean meditation",
              habits_add_custom(&habits, "Meditation", (Color){99, 196, 165, 255},
                                HABIT_SYNC_NONE, 0),
              0);
    habit_set_day(&habits, 0, 20250101, 1);
    habits_save(&habits);
    check_true("tickmate reimport", storage_import_zip(db_path));
    memset(&habits, 0, sizeof(habits));
    check_true("tickmate reimport load", storage_habits_load(&habits));
    check_int("tickmate reimport habit count", habits.count, 1);
    check_int("tickmate reimport enables counter", habits.items[0].counter_enabled, 1);
    check_int("tickmate reimport restores count", habit_day_count(&habits.items[0], 20250101), 3);
    storage_close();

    remove_tree(source);
    remove_tree(dest);
}

static void
test_external_tickmate_db_import(void)
{
    const char *db_path = getenv("APP_TICKMATE_IMPORT_FIXTURE");
    char dest[512];
    StorageImportInfo info;
    Habits habits;

    if(db_path == NULL || db_path[0] == '\0')
        return;

    make_clean_root(dest, sizeof(dest), "external-tickmate-dest");
    check_true("init external tickmate import dest", storage_init(dest));
    memset(&info, 0, sizeof(info));
    check_true("inspect external tickmate db", storage_inspect_import(db_path, &info));
    check_true("external tickmate db valid", info.valid);
    check_true("external tickmate db has habits", info.has_habits);
    check_true("external tickmate db import", storage_import_zip(db_path));
    memset(&habits, 0, sizeof(habits));
    check_true("external tickmate habits load", storage_habits_load(&habits));
    check_true("external tickmate habit count", habits.count > 0);
    storage_close();

    remove_tree(dest);
}

static void
test_checkin_backup_restore(void)
{
    char source[512], target[512], archive[1024], id[128];
    int duration = 60;
    StorageSessionCheckin saved = {0}, loaded = {0};
    make_clean_root(source, sizeof(source), "checkin-backup");
    make_clean_root(target, sizeof(target), "checkin-restored");
    snprintf(archive, sizeof(archive), "%s/backup.zip", source);
    check_true("checkin source", storage_init(source));
    check_true("checkin session", storage_save_session_for_activity(&duration, 1, 0, 1, id, sizeof(id)));
    saved.mood_before = 2;
    saved.mood_after = 4;
    saved.energy = 3;
    saved.stress = 1;
    snprintf(saved.note, sizeof(saved.note), "Quiet morning");
    snprintf(saved.tags, sizeof(saved.tags), "morning,home");
    check_true("save checkin", storage_save_session_checkin(id, &saved));
    check_true("export checkin", storage_export_zip(archive));
    storage_close();
    check_true("checkin target", storage_init(target));
    check_true("import checkin", storage_import_zip(archive));
    check_true("load restored checkin", storage_load_session_checkin(id, &loaded));
    check_true("restore all checkin fields", memcmp(&saved, &loaded, sizeof(saved)) == 0);
    saved.mood_after = 5;
    check_true("edit restored checkin", storage_save_session_checkin(id, &saved));
    check_true("reimport duplicate", storage_import_zip(archive));
    check_true("load retained local checkin", storage_load_session_checkin(id, &loaded));
    check_int("duplicate preserves local mood", loaded.mood_after, 5);
    check_int("duplicate does not add a session", storage_session_count(), 1);
    storage_close();
    remove_tree(source);
    remove_tree(target);
}

static void
test_legacy_database_filename_is_migrated(void)
{
    char root[512], current[512], old_path[512], marker[512];

    make_clean_root(root, sizeof(root), "legacy-database-name");
    write_source_database(root);
    make_path(current, sizeof(current), root, STORAGE_DB_NAME);
    make_path(old_path, sizeof(old_path), root, STORAGE_DB_NAME_LEGACY);
    snprintf(marker, sizeof(marker), "%s.migrated", current);
    check_true("move database to older filename", rename(current, old_path) == 0);
    check_true("upgrade older database", storage_init(root));
    check_int("older database sessions preserved", storage_session_count(), 1);
    storage_close();
    check_true("current database created", FileExists(current));
    check_true("older database retained", FileExists(old_path));
    check_true("completed-copy marker created", FileExists(marker));
    remove_tree(root);
}

static void
test_conflicting_database_names_fail_closed(void)
{
    char root[512], current[512], old_path[512];
    FILE *file;

    make_clean_root(root, sizeof(root), "database-name-conflict");
    write_source_database(root);
    make_path(current, sizeof(current), root, STORAGE_DB_NAME);
    make_path(old_path, sizeof(old_path), root, STORAGE_DB_NAME_LEGACY);
    file = fopen(old_path, "wb");
    check_true("create conflicting database file", file != NULL);
    if(file != NULL) {
        fputs("old data", file);
        fclose(file);
    }
    check_true("database name conflict fails closed", !storage_init(root));
    storage_close();
    check_true("current database preserved", FileExists(current));
    check_true("conflicting file preserved", FileExists(old_path));
    remove_tree(root);
}

int
main(void)
{
    test_legacy_database_filename_is_migrated();
    test_conflicting_database_names_fail_closed();
    test_checkin_backup_restore();
    test_raw_db_import();
    test_zip_db_import();
    test_current_archive_entry_import();
    test_habit_name_merge_import();
    test_import_conflict_prefers_data_over_empty();
    test_delete_all_resets_habits_to_empty_storage();
    test_delete_all_without_sync_account_does_not_queue_remote_deletes();
    test_deleted_habit_payload_clears_remote_days();
    test_import_modes_preserve_habits_and_settings_choice();
    test_unsupported_file_session_zip();
    test_historical_file_session_startup();
    test_tickmate_db_import();
    test_tickmate_reimport_recovers_counter_data();
    test_external_tickmate_db_import();
    test_onelist_import_and_sync_collections();
    test_deleted_list_defaults_stay_deleted();
    test_empty_initialized_habits_seed_meditation_on_startup();
    test_default_habits_can_wait_for_language_setup();
    test_existing_default_meditation_is_not_repaired_on_startup();
    test_sync_payload_omits_uploaded_state_after_upload_marker();
    test_sync_backfill_includes_existing_habits();
    test_sync_payload_excludes_local_settings();
    test_sync_payload_includes_queued_current_edits();
    test_sync_payload_includes_v6_encrypted_records();
    test_sync_ignores_plaintext_private_response();
    test_sync_rejects_unencrypted_outbox_record();
    test_sync_payload_batches_large_outbox();
    test_sync_outbox_preserves_edits_after_snapshot();
    test_sync_apply_preserves_counter_counts();
    test_sync_apply_clears_acknowledged_outbox_before_equal_timestamp_merge();
    test_sync_apply_sessions_last_write_wins();
    test_sync_apply_updates_habit_counter_enabled();
    test_stale_habit_save_keeps_synced_remote_habits();
    test_sync_payload_resets_cursor_for_orphan_habit_days();
    test_sync_payload_runs_one_time_habit_name_repair();
    test_sync_apply_merges_duplicate_habit_names();
    test_sync_apply_preserves_queued_habit_counter_enabled();
    test_session_linked_counts_materialize_for_sync();
    test_deleted_linked_session_clears_synced_habit_day();
    test_deleted_linked_session_preserves_manual_habit_count();
    test_existing_sessions_materialize_after_habit_save();
    test_sync_apply_meditation_logs_feed_profile_stats();
    test_profile_week_stats_combines_habits_and_practices();
    test_session_metadata();

    if(g_failures != 0) {
        fprintf(stderr, "%d storage import test failure(s)\n", g_failures);
        return 1;
    }
    printf("storage import tests passed\n");
    return 0;
}

void
TraceLog(int logLevel, const char *text, ...)
{
    (void)logLevel;
    (void)text;
}

bool
FileExists(const char *fileName)
{
    struct stat st;
    return fileName != NULL && stat(fileName, &st) == 0 && S_ISREG(st.st_mode);
}

const char *
GetFileName(const char *filePath)
{
    const char *slash;
    if(filePath == NULL)
        return "";
    slash = strrchr(filePath, '/');
    return slash != NULL ? slash + 1 : filePath;
}

const char *
GetWorkingDirectory(void)
{
    static char cwd[1024];
    if(getcwd(cwd, sizeof(cwd)) == NULL)
        snprintf(cwd, sizeof(cwd), ".");
    return cwd;
}

FilePathList
LoadDirectoryFiles(const char *dirPath)
{
    FilePathList files = {0};
    DIR *dir;
    struct dirent *entry;

    dir = opendir(dirPath);
    if(dir == NULL)
        return files;
    while((entry = readdir(dir)) != NULL) {
        if(strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
            continue;
        files.count++;
    }
    rewinddir(dir);
    files.paths = calloc(files.count, sizeof(char *));
    if(files.paths == NULL) {
        files.count = 0;
        closedir(dir);
        return files;
    }
    for(unsigned int i = 0; i < files.count && (entry = readdir(dir)) != NULL;) {
        char path[1024];
        if(strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
            continue;
        snprintf(path, sizeof(path), "%s/%s", dirPath, entry->d_name);
        files.paths[i] = strdup(path);
        if(files.paths[i] != NULL)
            i++;
    }
    closedir(dir);
    return files;
}

void
UnloadDirectoryFiles(FilePathList files)
{
    for(unsigned int i = 0; i < files.count; i++)
        free(files.paths[i]);
    free(files.paths);
}
