#ifndef STORAGE_H
#define STORAGE_H

#include "settings_api.h"
#include "sync_status_api.h"
#include <stddef.h>
#include <stdint.h>

enum {
    STORAGE_PATH_SIZE = 512,
    STORAGE_ID_SIZE = 64,
    SYNC_PROTOCOL_VERSION = 6
};

typedef struct StorageSessionCheckin {
    int mood_before;
    int mood_after;
    int energy;
    int stress;
    char note[256];
    char tags[160];
} StorageSessionCheckin;

typedef struct StorageMoodStats {
    int total;
    int counts[5];
    int average_after_x100;
    int average_lift_x100;
    int average_energy_x100;
    int average_stress_x100;
} StorageMoodStats;

typedef void (*StorageSessionRecordCallback)(const char *id,
                                                 int year, int month, int day,
                                                 int hour, int minute, int second,
                                                 int topic, int activity,
                                                 const int *rounds, int round_count,
                                                 void *user);

typedef enum StorageImportMode {
    STORAGE_IMPORT_DATA_ONLY = 0,
    STORAGE_IMPORT_DATA_AND_SETTINGS = 1
} StorageImportMode;

typedef struct StorageImportInfo {
    int valid;
    int has_sessions;
    int has_habits;
    int has_settings;
    int session_count;
    int habit_count;
    int setting_count;
} StorageImportInfo;

int storage_init(const char *root);
void storage_close(void);
const char *storage_db_path(void);
int storage_join_path(char *out, uint64_t out_size, const char *root, const char *name);
int storage_ensure_dir(const char *path);

const char *storage_get_setting_text(const char *key);
int storage_setting_text_equals(const char *key, const char *value);
int storage_has_sync_account(void);
int storage_get_social_cache_json(const char *kind, char *out, size_t out_size);
int storage_set_social_cache_json(const char *kind, const char *json);
int storage_json_array_count_path(const char *json, const char *path);
int storage_json_array_object_text(const char *json, const char *array_path,
                                   int index, const char *key,
                                   char *out, size_t out_size);
double storage_json_array_object_number(const char *json, const char *array_path,
                                        int index, const char *key);

int storage_save_session(const int *round_times, int round_count,
                              char *out_id, size_t out_id_size);
int storage_save_session_for_activity(const int *round_times, int round_count,
                                           int topic, int activity,
                                           char *out_id, size_t out_id_size);
int storage_save_session_at_for_activity(int local_date, int hour, int minute, int second,
                                         const int *round_times, int round_count,
                                         int topic, int activity,
                                         char *out_id, size_t out_id_size);
int storage_replace_session(const char *id, const int *round_times, int round_count);
int storage_delete_session(const char *id);
int storage_load_session(const char *id, int *round_times, int max_rounds,
                              int *year, int *month, int *day,
                              int *hour, int *minute, int *second);
int storage_save_session_checkin(const char *id,
                                 const StorageSessionCheckin *checkin);
int storage_load_session_checkin(const char *id,
                                 StorageSessionCheckin *checkin);
int storage_mood_stats(int activity_mask, int days,
                       StorageMoodStats *stats);
void storage_list_session_records(StorageSessionRecordCallback callback, void *user);
int storage_has_any(void);
int storage_session_count(void);
long long storage_session_change_clock(void);
int storage_habit_count(void);
int storage_habit_day_count(void);
long long storage_total_size(void);
int storage_profile_activity_stats(int activity, int today_date,
                                   int *streak_out, long *avg_hold_out);
int storage_profile_week_stats(int today_date, int *active_days_out,
                               int *practice_sessions_out);
long long storage_delete_all_sessions(void);
char *storage_build_sync_payload_json(const char *user_id_hash,
                                           const char *public_key_hex);
void storage_free_sync_payload_json(char *payload);
int storage_apply_sync_response_json(const char *response_json);
int storage_last_sync_changed(void);
int storage_sync_enabled(void);
void storage_set_sync_enabled(int connected);
int storage_sync_review_pending(void);
int storage_sync_review_details(char **local_out, char **remote_out);
int storage_sync_review_diff(char **diff_out);
int storage_sync_review_has_visible_diff(void);
int storage_sync_review_json_has_visible_diff(const char *json);
int storage_sync_review_json_should_auto_apply_remote(const char *json);
int storage_sync_review_clear_if_no_visible_diff(void);
int storage_sync_review_apply_remote_if_local_empty(void);
int storage_apply_pending_sync_review(int use_remote);
void storage_purge_synced_deleted_data(void);
const char *storage_sync_client_id(void);
void storage_make_uuid(char out[37]);
void storage_reset_sync_state(void);
void storage_enqueue_all_sync_state(void);
const char *storage_sync_data_owner_public_id(void);
void storage_set_sync_data_owner_public_id(const char *public_id);
int storage_has_local_syncable_data(void);
int storage_clear_local_syncable_data(void);

int storage_habits_empty(void);
int storage_habits_load(void *habits);
void storage_habits_save(const void *habits);
int storage_habit_day_save(const char *habit_id, int local_date, int completed, int count);
int storage_habits_initialized(void);
void storage_mark_habits_initialized(void);

int storage_elist_load(void *state);
void storage_elist_counts(int *lists, int *items);
int storage_elist_create_list(const char *title, char *out_id);
int storage_elist_update_list(const char *id, const char *title, int sort_order);
int storage_elist_delete_list(const char *id);
int storage_elist_create_item(const char *list_id, const char *title,
                              const char *comment, char *out_id);
int storage_elist_update_item(const char *id, const char *title,
                              const char *comment, int done, int sort_order);
int storage_elist_delete_item(const char *id);
int storage_elist_import_onelist(const char *path);

int storage_export_zip(const char *path);
int storage_export_sessions_csv(const char *path);
int storage_export_health_connect_csv(const char *path);
int storage_import_zip(const char *path);
int storage_import_zip_ex(const char *path, StorageImportMode mode);
int storage_inspect_import(const char *path, StorageImportInfo *info);

#endif
