#ifndef STORAGE_DB_H
#define STORAGE_DB_H

#include "storage.h"

#include <sqlite3.h>
#include <stddef.h>
#include <stdint.h>

static inline int *storage_sql_transaction_lock_held(void) {
#if defined(_MSC_VER)
    static __declspec(thread) int held;
#elif defined(__EMSCRIPTEN__) && !defined(__EMSCRIPTEN_PTHREADS__)
    static int held;
#else
    static __thread int held;
#endif
    return &held;
}

typedef struct StorageState {
    sqlite3 *db;
    char root[STORAGE_PATH_SIZE];
    char db_path[STORAGE_PATH_SIZE];
    char user_id[STORAGE_ID_SIZE];
    int last_sync_changed;
    int materialize_defer;
    int materialize_needed;
    int settings_write_depth;
    long long pending_sync_outbox_seq;
} StorageState;

extern StorageState g_storage;

long long now_seconds(void);
long long storage_local_timestamp(int year, int month, int day,
                                  int hour, int minute, int second);
int migrate_legacy_file_sessions_once(const char *root);
long long storage_next_change_time(void);
int bind_text(sqlite3_stmt *stmt, int index, const char *text);
long long db_select_int64(const char *sql, long long fallback);
int db_select_int(const char *sql, int fallback);
int db_exec_text(const char *sql, const char *text);
int storage_join_path(char *out, uint64_t out_size, const char *root, const char *name);
int path_exists(const char *path);
int migrate_data_root(const char *legacy, const char *current,
                      const char *archive_suffix, char *output,
                      uint64_t output_capacity);
int select_database_path(const char *legacy, const char *current,
                         const char *marker, const char *temporary,
                         const char *database_name, char *output,
                         uint64_t output_capacity);
int storage_ensure_dir(const char *path);
int exec_sql(const char *sql);
void *storage_db_handle(void);
char *storage_user_id_buffer(void);
void *storage_state_handle(void);
uint64_t storage_state_size(void);
char *storage_meta_text_buffer(void);
int schema_create(void);
int migrate_schema(void);
int load_or_create_user(void);
int meta_equals(const char *key, const char *value);
const char *get_meta_text(const char *key);
void set_meta(const char *key, const char *value);
long long get_meta_int64(const char *key, long long fallback);
void set_meta_int64(const char *key, long long value);

void storage_schedule_persist(void);
void storage_enqueue_all_sync_state(void);
int storage_enqueue_sync_habit(const char *habit_id);
int storage_enqueue_sync_habit_day(const char *habit_id, int local_date);
int storage_enqueue_sync_session(const char *session_id);
int storage_enqueue_sync_elist_list(const char *list_id);
int storage_enqueue_sync_elist_item(const char *item_id);
int storage_has_sync_account(void);
int storage_materialize_session_habit_days(void);
int storage_exec_json_user_sql(const char *sql, const char *json);
int storage_reconcile_remote_habit_ids(const char *response_json);
int storage_merge_duplicate_habit_names(void);
int storage_apply_sync_habits_json(const char *response_json);
int storage_apply_sync_habit_days_json(const char *response_json);
int storage_apply_sync_elist_lists_json(const char *response_json);
int storage_apply_sync_elist_items_json(const char *response_json);
int storage_migrate_default_habit_ids(void);
int storage_migrate_default_meditation_activity_mask(void);
int storage_migrate_habit_ids_to_uuid(void);
int storage_migrate_sync_enabled_flag(void);
int storage_sync_review_write_json(const char *json);
void storage_sync_review_delete_json(void);
int insert_session_at_ex(long long started_at, int local_date, const int *round_times,
                         int round_count, int topic, int activity, const char *source,
                         char *out_id, size_t out_id_size, int *out_inserted);
int storage_insert_legacy_session(long long started_at, int local_date,
                                  const int *round_times, int round_count);

#endif
