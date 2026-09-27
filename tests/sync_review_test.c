#include "storage.h"
#include "db.h"
#include "habits/habit_types.h"
#include "habits/habit_model.h"

#include <dirent.h>
#include <sqlite3.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
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
check_int(const char *label, int got, int want)
{
    if(got == want)
        return;
    fprintf(stderr, "FAIL %s: got %d, want %d\n", label, got, want);
    g_failures++;
}

static void
check_contains(const char *label, const char *text, const char *needle)
{
    if(text != NULL && strstr(text, needle) != NULL)
        return;
    fprintf(stderr, "FAIL %s: missing %s in %s\n", label, needle, text != NULL ? text : "(null)");
    g_failures++;
}

static void
check_not_contains(const char *label, const char *text, const char *needle)
{
    if(text == NULL || strstr(text, needle) == NULL)
        return;
    fprintf(stderr, "FAIL %s: unexpected %s in %s\n", label, needle, text);
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
    snprintf(out, out_size, "/tmp/breathing-sync-review-test-%ld-%s", (long)getpid(), name);
    remove_tree(out);
    check_true("create test root", ensure_dir(out));
    snprintf(g_data_root, sizeof(g_data_root), "%s", out);
}

static int
exec_db_sql(const char *root, const char *sql)
{
    char db_path[1024];
    sqlite3 *db = NULL;
    char *err = NULL;
    int ok;

    snprintf(db_path, sizeof(db_path), "%s/inbe.db", root);
    if(sqlite3_open(db_path, &db) != SQLITE_OK || db == NULL)
        return 0;
    ok = sqlite3_exec(db, sql, NULL, NULL, &err) == SQLITE_OK;
    if(!ok && err != NULL) {
        fprintf(stderr, "SQL error: %s\n", err);
        sqlite3_free(err);
    }
    sqlite3_close(db);
    return ok;
}

static int
read_db_count(const char *root, const char *sql)
{
    char db_path[1024];
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int count = -1;

    snprintf(db_path, sizeof(db_path), "%s/inbe.db", root);
    if(sqlite3_open(db_path, &db) != SQLITE_OK || db == NULL)
        return count;
    if(sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK &&
       sqlite3_step(stmt) == SQLITE_ROW)
        count = sqlite3_column_int(stmt, 0);
    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return count;
}

static void
seed_local_data(const char *root)
{
    check_true("seed local data",
               exec_db_sql(root, "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                                 "sync_mode,sync_activity,counter_enabled,sort_order,deleted_at,"
                                 "updated_at)"
                                 "VALUES('local-habit',(SELECT id FROM users LIMIT 1),'Local "
                                 "Breath',10,20,30,0,0,1,1,0,1782300000);"
                                 "INSERT INTO "
                                 "habit_days(habit_id,local_date,completed,count,session_count,"
                                 "updated_at)"
                                 "VALUES('local-habit',20260624,1,4,0,1782300000);"
                                 "INSERT INTO "
                                 "sessions(id,user_id,started_at,local_date,topic,activity,source,"
                                 "imported_at,rounds_hash,deleted_at,updated_at)"
                                 "VALUES('local-session',(SELECT id FROM users LIMIT "
                                 "1),1782300000,20260624,1,1,'test',1782300000,101,0,1782300000);"
                                 "INSERT INTO session_rounds(session_id,round_index,seconds)"
                                 "VALUES('local-session',0,40);"));
}

static void
mark_local_data_pending(const char *root)
{
    check_true("mark local data pending",
               exec_db_sql(root, "INSERT OR REPLACE INTO "
                                 "sync_outbox(entity_type,entity_id,local_date,queued_at)"
                                 "VALUES('habit','local-habit',0,1782300000);"
                                 "INSERT OR REPLACE INTO "
                                 "sync_outbox(entity_type,entity_id,local_date,queued_at)"
                                 "VALUES('habit_day','local-habit',20260624,1782300000);"
                                 "INSERT OR REPLACE INTO "
                                 "sync_outbox(entity_type,entity_id,local_date,queued_at)"
                                 "VALUES('session','local-session',0,1782300000);"));
}

static void
mark_empty_local_pending(const char *root)
{
    check_true("mark empty local pending",
               exec_db_sql(root, "INSERT OR REPLACE INTO "
                                 "sync_outbox(entity_type,entity_id,local_date,queued_at)"
                                 "VALUES('account','alias',0,1782300000);"));
}

static void
seed_local_habit_without_activity(const char *root)
{
    check_true("seed local habit without activity",
               exec_db_sql(root, "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                                 "sync_mode,sync_activity,counter_enabled,sort_order,deleted_at,"
                                 "updated_at)"
                                 "VALUES('empty-local-habit',(SELECT id FROM users LIMIT 1),"
                                 "'Empty Habit',10,20,30,0,0,1,1,0,1782300000);"));
}

static void
seed_local_session_only(const char *root)
{
    check_true("seed local session only",
               exec_db_sql(root, "INSERT INTO "
                                 "sessions(id,user_id,started_at,local_date,topic,activity,source,"
                                 "imported_at,rounds_hash,deleted_at,updated_at)"
                                 "VALUES('tiny-local-session',(SELECT id FROM users LIMIT "
                                 "1),1782300000,20260624,1,1,'test',1782300000,101,0,1782300000);"
                                 "INSERT INTO session_rounds(session_id,round_index,seconds)"
                                 "VALUES('tiny-local-session',0,40);"));
}

static void
mark_local_session_only_pending(const char *root)
{
    check_true("mark local session only pending",
               exec_db_sql(root, "INSERT OR REPLACE INTO "
                                 "sync_outbox(entity_type,entity_id,local_date,queued_at)"
                                 "VALUES('session','tiny-local-session',0,1782300000);"));
}

static void
seed_test_private_record_key(void)
{
    char private_key[5121];
    for(size_t i = 0; i < sizeof(private_key) - 1; i++)
        private_key[i] = (i % 2) == 0 ? '4' : '2';
    private_key[sizeof(private_key) - 1] = '\0';
    storage_set_setting_text("sync_private_key", private_key);
}

static void
mark_pending_payload_in_flight(void)
{
    seed_test_private_record_key();
    char *payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_true("pending payload builds", payload != NULL);
    storage_free_sync_payload_json(payload);
}

static void
seed_local_yoga_data(const char *root)
{
    check_true("seed local yoga data",
               exec_db_sql(root, "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                                 "sync_mode,sync_activity,counter_enabled,sort_order,deleted_"
                                 "at,updated_at)"
                                 "VALUES('yoga',(SELECT id FROM users LIMIT "
                                 "1),'Yoga',239,178,102,1,4,0,1,0,1782300000);"
                                 "INSERT INTO "
                                 "habit_days(habit_id,local_date,completed,count,session_"
                                 "count,updated_at)"
                                 "VALUES('yoga',20260624,1,2,0,1782300000);"));
}

static const char *
remote_snapshot_response(void)
{
    return "{"
           "\"server_version\":12,"
           "\"server_state_hash\":\"remote-hash-001\","
           "\"full_snapshot_required\":true,"
           "\"changes_complete\":false,"
           "\"changes\":{"
           "\"habits\":[{\"id\":\"remote-habit\",\"name\":\"Remote Breath\","
           "\"color_r\":90,\"color_g\":80,\"color_b\":70,\"sync_mode\":0,"
           "\"sync_activity\":0,\"counter_enabled\":1,\"sort_order\":1,"
           "\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:00:00Z\"}],"
           "\"habit_days\":[{\"habit_id\":\"remote-habit\",\"local_date\":"
           "20260624,"
           "\"completed\":true,\"count\":7,\"updated_at\":\"2026-06-24T10:00:"
           "00Z\"}],"
           "\"sessions\":[{\"id\":\"remote-session\",\"started_at\":\"2026-06-"
           "24T10:00:00Z\","
           "\"local_date\":20260624,\"topic\":2,\"activity\":2,\"source\":\"sync-"
           "test\","
           "\"rounds_hash\":202,\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:"
           "00:00Z\","
           "\"rounds\":[{\"round_index\":0,\"hold_seconds\":55}]}],"
           "\"meditation_logs\":[]"
           "}"
           "}";
}

static const char *
deleted_only_remote_snapshot_response(void)
{
    return "{"
           "\"server_version\":13,"
           "\"server_state_hash\":\"remote-hash-deleted\","
           "\"full_snapshot_required\":true,"
           "\"changes_complete\":false,"
           "\"changes\":{"
           "\"habits\":[],"
           "\"habit_days\":[],"
           "\"sessions\":[{\"id\":\"deleted-session\",\"started_at\":\"2026-06-"
           "24T10:00:00Z\","
           "\"local_date\":20260624,\"topic\":2,\"activity\":3,\"source\":\"sync-"
           "test\","
           "\"rounds_hash\":202,\"deleted_at\":1782300000,\"updated_at\":\"2026-"
           "06-24T10:00:00Z\","
           "\"rounds\":[{\"round_index\":0,\"hold_seconds\":55}]}],"
           "\"meditation_logs\":[]"
           "}"
           "}";
}

static const char *
remote_additive_yoga_response(void)
{
    return "{"
           "\"server_version\":14,"
           "\"server_state_hash\":\"remote-hash-yoga\","
           "\"full_snapshot_required\":true,"
           "\"changes_complete\":false,"
           "\"changes\":{"
           "\"habits\":[{\"id\":\"yoga\",\"name\":\"Yoga\","
           "\"color_r\":239,\"color_g\":178,\"color_b\":102,\"sync_mode\":1,"
           "\"sync_activity\":4,\"counter_enabled\":0,\"sort_order\":1,"
           "\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:00:00Z\"}],"
           "\"habit_days\":[{\"habit_id\":\"yoga\",\"local_date\":20260624,"
           "\"completed\":true,\"count\":1,\"updated_at\":\"2026-06-24T10:00:"
           "00Z\"}],"
           "\"sessions\":[{\"id\":\"sun-session\",\"started_at\":\"2026-06-24T10:"
           "00:00Z\","
           "\"local_date\":20260624,\"topic\":0,\"activity\":2,\"source\":"
           "\"test\","
           "\"rounds_hash\":303,\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:"
           "00:00Z\","
           "\"rounds\":[{\"round_index\":0,\"hold_seconds\":1}]}],"
           "\"meditation_logs\":[]"
           "}"
           "}";
}

static const char *
remote_clean_v3_response(void)
{
    return "{"
           "\"server_version\":21,"
           "\"server_clock\":22,"
           "\"server_state_hash\":\"remote-clean-v3\","
           "\"data\":{"
           "\"habits\":[{\"id\":\"clean-habit\",\"name\":\"Clean Breath\","
           "\"color_r\":12,\"color_g\":34,\"color_b\":56,\"sync_mode\":0,"
           "\"sync_activity\":0,\"counter_enabled\":1,\"sort_order\":3,"
           "\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:00:00Z\"}],"
           "\"habit_days\":[{\"habit_id\":\"clean-habit\",\"local_date\":20260624,"
           "\"completed\":true,\"count\":5,\"updated_at\":\"2026-06-24T10:00:00Z\"}],"
           "\"sessions\":[{\"id\":\"clean-session\",\"started_at\":\"2026-06-24T10:00:00Z\","
           "\"local_date\":20260624,\"topic\":2,\"activity\":2,\"source\":\"sync-test\","
           "\"rounds_hash\":505,\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:00:00Z\","
           "\"rounds\":[{\"round_index\":0,\"hold_seconds\":44}]}],"
           "\"meditation_logs\":[]"
           "},"
           "\"changes\":{\"habits\":[],\"habit_days\":[],\"sessions\":[],\"meditation_logs\":[]}"
           "}";
}

static const char *
remote_tiny_session_snapshot_response(void)
{
    return "{"
           "\"server_version\":15,"
           "\"server_state_hash\":\"remote-hash-tiny-session\","
           "\"full_snapshot_required\":true,"
           "\"changes_complete\":false,"
           "\"changes\":{"
           "\"habits\":[],"
           "\"habit_days\":[],"
           "\"sessions\":[{\"id\":\"tiny-remote-session\",\"started_at\":\"2026-06-24T10:"
           "05:00Z\","
           "\"local_date\":20260624,\"topic\":1,\"activity\":1,\"source\":\"sync-"
           "test\","
           "\"rounds_hash\":404,\"deleted_at\":0,\"updated_at\":\"2026-06-24T10:"
           "05:00Z\","
           "\"rounds\":[{\"round_index\":0,\"hold_seconds\":55}]}],"
           "\"meditation_logs\":[]"
           "}"
           "}";
}

static void
test_full_snapshot_with_pending_local_edits_syncs_without_review(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "pending");
    check_true("init pending db", storage_init(root));
    seed_local_data(root);
    mark_local_data_pending(root);
    seed_test_private_record_key();
    mark_pending_payload_in_flight();

    check_true("apply review response",
               storage_apply_sync_response_json(remote_snapshot_response()));
    check_false("review not pending for local edits", storage_sync_review_pending());
    check_int("local session preserved",
              read_db_count(root, "SELECT COUNT(*) FROM sessions WHERE id='local-session'"), 1);
    check_int("remote session merged",
              read_db_count(root, "SELECT COUNT(*) FROM sessions WHERE id='remote-session'"), 1);
    check_int("local habit preserved",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='local-habit'"), 1);
    check_int("remote habit merged",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='remote-habit'"), 1);
    check_int("pending local edits cleared after accepted sync",
              read_db_count(root, "SELECT COUNT(*) FROM sync_outbox"), 0);

    storage_close();
    remove_tree(root);
}

static void
test_tiny_pending_snapshot_syncs_without_review(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "tiny-pending");
    check_true("init tiny pending db", storage_init(root));
    seed_local_session_only(root);
    mark_local_session_only_pending(root);
    mark_pending_payload_in_flight();

    check_true("apply tiny review response",
               storage_apply_sync_response_json(remote_tiny_session_snapshot_response()));
    check_false("tiny review not pending", storage_sync_review_pending());
    check_int("tiny local session preserved",
              read_db_count(root,
                            "SELECT COUNT(*) FROM sessions WHERE id='tiny-local-session'"),
              1);
    check_int("tiny remote session merged",
              read_db_count(root,
                            "SELECT COUNT(*) FROM sessions WHERE id='tiny-remote-session'"),
              1);
    check_int("tiny outbox cleared",
              read_db_count(root, "SELECT COUNT(*) FROM sync_outbox"), 0);

    storage_close();
    remove_tree(root);
}

static void
test_empty_local_pending_snapshot_applies_remote(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "empty-local-pending");
    check_true("init empty local pending db", storage_init(root));
    mark_empty_local_pending(root);
    mark_pending_payload_in_flight();

    check_true("apply empty local review response",
               storage_apply_sync_response_json(remote_snapshot_response()));
    check_false("empty local review not pending", storage_sync_review_pending());
    check_false("empty local review cleared", storage_sync_review_pending());
    check_int("empty local remote session applied",
              read_db_count(root, "SELECT COUNT(*) FROM sessions WHERE id='remote-session'"), 1);
    check_int("empty local remote habit applied",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='remote-habit'"), 1);
    check_int("empty local outbox cleared",
              read_db_count(root, "SELECT COUNT(*) FROM sync_outbox"), 0);

    storage_close();
    remove_tree(root);
}

static void
test_local_habit_without_activity_does_not_force_review(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "empty-habit-local");
    check_true("init empty habit local db", storage_init(root));
    seed_local_habit_without_activity(root);
    mark_empty_local_pending(root);
    mark_pending_payload_in_flight();

    check_true("apply empty habit local response",
               storage_apply_sync_response_json(remote_snapshot_response()));
    check_false("empty habit local review not pending", storage_sync_review_pending());
    check_int("empty habit local remote session applied",
              read_db_count(root, "SELECT COUNT(*) FROM sessions WHERE id='remote-session'"), 1);
    check_int("empty habit local remote habit applied",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='remote-habit'"), 1);
    check_int("empty habit local outbox cleared",
              read_db_count(root, "SELECT COUNT(*) FROM sync_outbox"), 0);

    storage_close();
    remove_tree(root);
}

static void
test_review_ignores_deleted_remote_rows(void)
{
    char root[1024];
    char *diff_detail = NULL;

    make_clean_root(root, sizeof(root), "deleted-review");
    check_true("init deleted review db", storage_init(root));
    check_true("apply deleted review response",
               storage_apply_sync_response_json(deleted_only_remote_snapshot_response()));
    check_false("deleted-only review not pending", storage_sync_review_pending());
    check_true("deleted review json has no visible diff",
               !storage_sync_review_json_has_visible_diff(deleted_only_remote_snapshot_response()));
    check_true("deleted review diff builds", storage_sync_review_diff(&diff_detail));
    check_not_contains("deleted remote hidden from diff", diff_detail, "deleted-session");
    check_not_contains("deleted remote marker hidden from diff", diff_detail, "deleted");

    free(diff_detail);
    storage_close();
    remove_tree(root);
}

static void
test_remote_additions_apply_without_review(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "remote-additive");
    check_true("init remote additive db", storage_init(root));
    check_true("apply remote additive response",
               storage_apply_sync_response_json(remote_additive_yoga_response()));
    check_false("remote additive review not pending", storage_sync_review_pending());
    check_int("remote additive sun session applied",
              read_db_count(root, "SELECT COUNT(*) FROM sessions WHERE id='sun-session'"), 1);
    check_int(
        "remote additive yoga habit applied",
        read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='yoga' AND counter_enabled=0"),
        1);
    check_int(
        "remote additive yoga day applied",
        read_db_count(root, "SELECT COUNT(*) FROM habit_days WHERE habit_id='yoga' AND count=1"),
        1);

    storage_close();
    remove_tree(root);
}

static void
test_clean_v3_data_applies_inside_existing_transaction(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "clean-v3-nested");
    check_true("init clean v3 db", storage_init(root));
    check_true("begin outer transaction", exec_sql("BEGIN IMMEDIATE"));
    check_true("apply clean v3 response", storage_apply_sync_response_json(remote_clean_v3_response()));
    check_true("commit outer transaction", exec_sql("COMMIT"));
    check_int("clean v3 habit applied",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='clean-habit'"), 1);
    check_int("clean v3 day applied",
              read_db_count(root, "SELECT COUNT(*) FROM habit_days WHERE habit_id='clean-habit' "
                                  "AND count=5"),
              1);
    check_int("clean v3 session applied",
              read_db_count(root, "SELECT COUNT(*) FROM sessions WHERE id='clean-session'"), 1);
    check_int("clean v3 rounds applied",
              read_db_count(root, "SELECT COUNT(*) FROM session_rounds WHERE "
                                  "session_id='clean-session' AND seconds=44"),
              1);

    storage_close();
    remove_tree(root);
}

static void
test_clean_v3_habit_ids_replace_local_uuid_by_name(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "clean-v3-id-repair");
    check_true("init clean v3 repair db", storage_init(root));
    check_true("seed local mismatched uuid",
               exec_db_sql(root, "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                                 "sync_mode,sync_activity,counter_enabled,sort_order,deleted_at,"
                                 "updated_at)"
                                 "VALUES('local-clean-id',(SELECT id FROM users LIMIT 1),"
                                 "'Clean Breath',9,9,9,0,0,1,3,0,1782200000);"
                                 "INSERT INTO habit_days(habit_id,local_date,completed,count,"
                                 "session_count,updated_at)"
                                 "VALUES('local-clean-id',20260623,1,2,0,1782200000);"));
    check_true("apply clean v3 repair response",
               storage_apply_sync_response_json(remote_clean_v3_response()));
    check_int("local duplicate id removed",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='local-clean-id'"), 0);
    check_int("canonical remote id present",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='clean-habit'"), 1);
    check_int("local day moved to canonical id",
              read_db_count(root, "SELECT COUNT(*) FROM habit_days WHERE habit_id='clean-habit' "
                                  "AND local_date=20260623 AND count=2"),
              1);
    check_int("remote day still applied",
              read_db_count(root, "SELECT COUNT(*) FROM habit_days WHERE habit_id='clean-habit' "
                                  "AND local_date=20260624 AND count=5"),
              1);

    storage_close();
    remove_tree(root);
}

static void
test_uuid_habit_ids_load_days_into_memory(void)
{
    char root[1024];
    Habits habits;
    const char *uuid = "940dd8b7-0d60-48ce-9c8f-433b9170b6b1";

    make_clean_root(root, sizeof(root), "uuid-habit-load");
    memset(&habits, 0, sizeof(habits));
    check_true("init uuid habit load db", storage_init(root));
    check_true("seed uuid habit day",
               exec_db_sql(root, "INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,"
                                 "sync_mode,sync_activity,counter_enabled,sort_order,deleted_at,"
                                 "updated_at)"
                                 "VALUES('940dd8b7-0d60-48ce-9c8f-433b9170b6b1',"
                                 "(SELECT id FROM users LIMIT 1),'Meditation',1,2,3,0,0,1,0,0,"
                                 "1782200000);"
                                 "INSERT INTO habit_days(habit_id,local_date,completed,count,"
                                 "session_count,updated_at)"
                                 "VALUES('940dd8b7-0d60-48ce-9c8f-433b9170b6b1',20260629,1,1,0,"
                                 "1782200000);"));
    check_true("load uuid habits", storage_habits_load(&habits));
    check_int("uuid habit count", habits.count, 1);
    check_contains("uuid id not truncated", habits.items[0].id, uuid);
    check_int("uuid habit day loaded", habits.items[0].day_count, 1);
    if(habits.items[0].day_count > 0)
        check_int("uuid habit day date", habits.items[0].days[0].day_index, 20260629);

    habits_free(&habits);
    storage_close();
    remove_tree(root);
}

static void
test_remote_snapshot_removes_absent_local_yoga_without_pending_edits(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "remote-removes-yoga");
    check_true("init remote removes yoga db", storage_init(root));
    seed_local_yoga_data(root);
    check_true("apply remote deleted yoga response",
               storage_apply_sync_response_json(deleted_only_remote_snapshot_response()));
    check_false("remote deleted yoga review not pending", storage_sync_review_pending());
    check_int("remote deleted yoga habit removed",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='yoga'"), 0);
    check_int("remote deleted yoga day removed",
              read_db_count(root, "SELECT COUNT(*) FROM habit_days WHERE habit_id='yoga'"), 0);

    storage_close();
    remove_tree(root);
}

static void
test_remote_snapshot_keeps_review_for_pending_yoga_delete(void)
{
    char root[1024];

    make_clean_root(root, sizeof(root), "remote-removes-yoga-pending");
    check_true("init pending yoga delete db", storage_init(root));
    seed_local_yoga_data(root);
    check_true("mark local yoga pending",
               exec_db_sql(root, "INSERT OR REPLACE INTO "
                                 "sync_outbox(entity_type,entity_id,local_date,queued_at)"
                                 "VALUES('habit','yoga',0,1782300000);"));
    mark_pending_payload_in_flight();
    check_true("apply pending remote deleted yoga response",
               storage_apply_sync_response_json(deleted_only_remote_snapshot_response()));
    check_false("pending yoga delete does not require review", storage_sync_review_pending());
    check_int("pending yoga still local after merge",
              read_db_count(root, "SELECT COUNT(*) FROM habits WHERE id='yoga'"), 1);

    storage_close();
    remove_tree(root);
}

static void
test_sync_payload_uses_encrypted_records(void)
{
    char root[1024];
    char *payload;

    make_clean_root(root, sizeof(root), "encrypted-payload");
    check_true("init encrypted payload db", storage_init(root));
    seed_local_data(root);
    mark_local_data_pending(root);
    check_int("obsolete sync ops table removed",
              read_db_count(root, "SELECT COUNT(*) FROM sqlite_master WHERE "
                                  "type='table' AND name='sync_ops'"),
              0);

    seed_test_private_record_key();
    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_contains("v6 payload protocol", payload, "\"protocol_version\":6");
    check_contains("v6 payload app id", payload, "\"app_id\":\"inbe\"");
    check_contains("v6 payload capabilities", payload, "\"client_capabilities\"");
    check_not_contains("v6 payload has no legacy data opt-in", payload, "include_legacy_data");
    check_contains("v6 payload client clock", payload, "\"client_clock\":0");
    check_not_contains("v6 payload has no plaintext operations", payload, "\"ops\":");
    check_contains("v6 payload includes encrypted records", payload, "\"encrypted_records\":[");
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_normal_response_records_server_hash(void)
{
    char root[1024];
    char *payload;
    StorageSyncStatus status;
    const char *response = "{"
                           "\"protocol_version\":6,"
                           "\"server_version\":5,"
                           "\"server_clock\":77,"
                           "\"server_state_hash\":\"normal-hash-001\","
                           "\"account_alias\":\"waozi\","
                           "\"changes\":{\"encrypted_records\":[]}"
                           "}";

    make_clean_root(root, sizeof(root), "normal");
    check_true("init normal db", storage_init(root));
    check_true("apply normal response", storage_apply_sync_response_json(response));
    check_false("normal response no review", storage_sync_review_pending());
    check_contains("normal response saves alias", storage_get_setting_text("sync_account_alias"),
                   "waozi");
    check_true("normal response loads status", storage_sync_status(&status));
    check_int("normal response server version", status.server_version, 5);
    check_int("normal response server clock", status.server_clock, 77);

    seed_test_private_record_key();
    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_contains("normal response hash in next payload", payload,
                   "\"last_server_state_hash\":\"normal-hash-001\"");
    check_contains("normal response clock in next payload", payload, "\"client_clock\":77");
    check_not_contains("normal response no full replace", payload, "full_sync_requested");
    storage_free_sync_payload_json(payload);

    storage_close();
    remove_tree(root);
}

static void
test_social_cache_is_server_authored_sync_state(void)
{
    char root[1024];
    char cached[512];
    char *payload;
    const char *response = "{"
                           "\"server_version\":9,"
                           "\"server_clock\":9,"
                           "\"server_state_hash\":\"social-hash-001\","
                           "\"changes\":{\"habits\":[],\"habit_days\":[],"
                           "\"sessions\":[],\"meditation_logs\":[],"
                           "\"social_cache\":[{\"kind\":\"friends.list\","
                           "\"json\":{\"friends\":[{\"user_id_hash\":\"server-friend\"}]},"
                           "\"updated_at\":\"2026-06-28T00:00:00Z\"}]}"
                           "}";

    make_clean_root(root, sizeof(root), "social-cache");
    check_true("init social cache db", storage_init(root));

    check_true("store local social cache",
               storage_set_social_cache_json("friends.list",
                                             "{\"friends\":[{\"user_id_hash\":\"local-edit\"}]}"));
    check_false("social cache alone is not local syncable data",
                storage_has_local_syncable_data());
    seed_test_private_record_key();
    payload = storage_build_sync_payload_json("test-public-id", "test-public-key");
    check_not_contains("social cache not uploaded as typed data", payload, "social_cache");
    check_not_contains("social cache not uploaded as op", payload, "friends.list");
    storage_free_sync_payload_json(payload);

    check_true("apply server social cache", storage_apply_sync_response_json(response));
    check_true("load server social cache",
               storage_get_social_cache_json("friends.list", cached, sizeof(cached)));
    check_contains("server social cache replaces local edit", cached, "server-friend");
    check_not_contains("local social cache edit removed", cached, "local-edit");

    storage_close();
    remove_tree(root);
}

int
main(void)
{
    setenv("TZ", "UTC", 1);
    tzset();

    test_full_snapshot_with_pending_local_edits_syncs_without_review();
    test_tiny_pending_snapshot_syncs_without_review();
    test_empty_local_pending_snapshot_applies_remote();
    test_local_habit_without_activity_does_not_force_review();
    test_review_ignores_deleted_remote_rows();
    test_remote_additions_apply_without_review();
    test_clean_v3_data_applies_inside_existing_transaction();
    test_clean_v3_habit_ids_replace_local_uuid_by_name();
    test_uuid_habit_ids_load_days_into_memory();
    test_remote_snapshot_removes_absent_local_yoga_without_pending_edits();
    test_remote_snapshot_keeps_review_for_pending_yoga_delete();
    test_sync_payload_uses_encrypted_records();
    test_normal_response_records_server_hash();
    test_social_cache_is_server_authored_sync_state();

    if(g_failures != 0) {
        fprintf(stderr, "%d failures\n", g_failures);
        return 1;
    }
    printf("sync review tests passed\n");
    return 0;
}
