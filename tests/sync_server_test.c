#include "storage.h"
#include "sync_account.h"
#include "sync_client.h"
#include "habits/habit_types.h"
#include "screens/elist_types.h"
#include <curl/curl.h>
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static char current_root[1024];
static size_t
discard_http_body(char *data, size_t size, size_t count, void *user)
{
    (void)data;
    (void)user;
    return size * count;
}
static void
check_loopback_http(const char *base_url)
{
    char url[256];
    char error[CURL_ERROR_SIZE] = {0};
    CURL *curl = curl_easy_init();
    CURLcode result;
    long status = 0;
    assert(curl != NULL);
    snprintf(url, sizeof(url), "%s/healthz", base_url);
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, error);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, discard_http_body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);
    result = curl_easy_perform(curl);
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
    if(result != CURLE_OK || status != 200) {
        fprintf(stderr, "loopback HTTP probe failed: curl=%d (%s), status=%ld, detail=%s\n",
                (int)result, curl_easy_strerror(result), status, error);
        curl_easy_cleanup(curl);
        exit(1);
    }
    curl_easy_cleanup(curl);
}
void data_init(void) {}
const char *data_root(void) { return current_root; }
void TraceLog(int level, const char *fmt, ...) {
    (void)level;
    va_list args; va_start(args, fmt); vfprintf(stderr, fmt, args); va_end(args);
    fputc('\n', stderr);
}
static void open_client(const char *root) {
    storage_close();
    snprintf(current_root, sizeof(current_root), "%s", root);
    assert(storage_init(root));
}
static void expect_habit(const char *id, const char *name, int date) {
    Habits *habits = calloc(1, sizeof(*habits));
    Habit *habit = NULL;
    assert(habits != NULL);
    assert(storage_habits_load(habits));
    for(int i = 0; i < habits->count; i++)
        if(strcmp(habits->items[i].id, id) == 0) habit = &habits->items[i];
    assert(habit != NULL);
    assert(strcmp(habit->name, name) == 0);
    assert(habit->day_count == 1);
    assert(habit->days[0].day_index == date);
    assert(habit->days[0].completed);
    assert(habit->days[0].count == 1);
    habits_free(habits);
    free(habits);
}
static void seed_default_habits(void) {
    Habits *habits = calloc(1, sizeof(*habits));
    assert(habits != NULL);
    habits->count = 2;
    snprintf(habits->items[0].id, sizeof(habits->items[0].id), "meditation");
    snprintf(habits->items[0].name, sizeof(habits->items[0].name), "Meditation");
    snprintf(habits->items[1].id, sizeof(habits->items[1].id), "yoga");
    snprintf(habits->items[1].name, sizeof(habits->items[1].name), "Yoga");
    for(int i = 0; i < habits->count; i++) {
        habits->items[i].color = (Color){126, 183, 230, 255};
        habits->items[i].counter_target = 1;
        habits->items[i].reminder_hour = -1;
    }
    storage_habits_save(habits);
    free(habits);
    assert(storage_habit_count() == 2);
}
static void expect_list(const char *list_id, const char *item_id,
                        const char *title, const char *comment, int done) {
    EListState state = {0};
    int found_list = 0, found_item = 0;
    int lists = 0, items = 0;
    assert(storage_elist_load(&state));
    storage_elist_counts(&lists, &items);
    assert(lists > 0 && items > 0);
    for(int i = 0; i < state.list_count; i++)
        if(strcmp(state.lists[i].id, list_id) == 0 &&
           strcmp(state.lists[i].title, title) == 0) found_list = 1;
    for(int i = 0; i < state.item_count; i++)
        if(strcmp(state.items[i].id, item_id) == 0 &&
           strcmp(state.items[i].list_id, list_id) == 0 &&
           strcmp(state.items[i].comment, comment) == 0 &&
           state.items[i].done == done) found_item = 1;
    assert(found_list && found_item);
}
static void synchronize(const char *url) {
    for(int attempt = 0; attempt < 8; attempt++) {
        SyncResult result = sync_client_connect(url);
        if(result != SYNC_OK) {
            fprintf(stderr, "sync attempt %d failed: %s\n", attempt + 1,
                    GetSyncResultName(result));
            if(attempt == 7) exit(1);
            sleep(2);
            continue;
        }
        if(storage_sync_review_pending()) {
            assert(storage_sync_review_apply_remote_if_local_empty());
            assert(!storage_sync_review_pending());
        }
        StorageSyncStatus status;
        assert(storage_sync_status(&status));
        if(!status.queued_changes) return;
    }
    fprintf(stderr, "sync did not drain queued changes\n");
    exit(1);
}
int main(int argc, char **argv) {
    if(argc == 4 && strcmp(argv[3], "--recovery-probe") == 0) {
        open_client(argv[2]);
        SyncResult result = sync_client_connect(argv[1]);
        printf("RECOVERY_PROBE result=%s habits=%d sessions=%d\n",
               GetSyncResultName(result), storage_habit_count(),
               storage_session_count());
        storage_close();
        return result == SYNC_OK ? 0 : 1;
    }
    if(argc == 4 && strcmp(argv[3], "--cleanup") == 0) {
        open_client(argv[2]);
        storage_set_setting_text("sync_server_url", argv[1]);
        storage_set_sync_enabled(1);
        SyncResult result = sync_client_delete_account(argv[1]);
        storage_close();
        if(result != SYNC_OK) {
            fprintf(stderr, "cleanup failed: %s\n", GetSyncResultName(result));
            return 1;
        }
        puts("PASS disposable account cleanup");
        return 0;
    }
    SyncAccount account = {0};
    char a[1024], b[1024], backup[1024], restored[1024], id[256], other_id[256];
    int duration = 60;
    StorageSessionCheckin checkin = {0}, loaded = {0};
    assert(argc == 4 || (argc == 5 &&
           (strcmp(argv[4], "--live") == 0 || strcmp(argv[4], "--moto-setup") == 0)));
    int live = argc == 5;
    int moto_setup = live && strcmp(argv[4], "--moto-setup") == 0;
    /* The normal runner supplies a fresh loopback server and disposable data root. */
    assert(live || strncmp(argv[1], "http://127.0.0.1:", 17) == 0);
    assert(strncmp(argv[3], "http://127.0.0.1:", 17) == 0);
    if(!live)
        check_loopback_http(argv[1]);
    char alias[40], friend_alias[40];
    snprintf(alias, sizeof(alias), "restore_%ld", (long)getpid());
    snprintf(friend_alias, sizeof(friend_alias), "friend_%ld", (long)getpid());
    snprintf(a, sizeof(a), "%s/a", argv[2]);
    snprintf(b, sizeof(b), "%s/b", argv[2]);
    snprintf(restored, sizeof(restored), "%s/restored", argv[2]);
    snprintf(backup, sizeof(backup), "%s/backup.zip", argv[2]);
    open_client(a);
    assert(sync_account_generate(&account));
    assert(sync_account_save(&account, 0) == SYNC_ACCOUNT_SAVE_OK);
    const char *habit_id = "00000000-0000-4000-8000-000000000042";
    const char *habit_name = "Recovery meditation";
    const int habit_date = 20260919;
    Habits *habits = calloc(1, sizeof(*habits));
    assert(habits != NULL);
    habits->count = 1;
    snprintf(habits->items[0].id, sizeof(habits->items[0].id), "%s", habit_id);
    snprintf(habits->items[0].name, sizeof(habits->items[0].name), "%s", habit_name);
    habits->items[0].color = (Color){82, 119, 193, 255};
    habits->items[0].counter_target = 1;
    habits->items[0].reminder_hour = -1;
    storage_habits_save(habits);
    free(habits);
    assert(storage_habit_day_save(habit_id, habit_date, 1, 1));
    expect_habit(habit_id, habit_name, habit_date);
    assert(storage_save_session_for_activity(&duration, 1, 0, 1, id, sizeof(id)));
    checkin.mood_after = 4;
    assert(storage_save_session_checkin(id, &checkin));
    assert(sync_client_connect("http://127.0.0.1:1") != SYNC_OK);
    assert(storage_session_count() == 1); /* Offline failure retains local work. */
    open_client(a);
    assert(storage_load_session_checkin(id, &loaded) && loaded.mood_after == 4);
    /* Server commits the upload, but the proxy drops its response. */
    assert(sync_client_connect(argv[3]) != SYNC_OK);
    open_client(a);
    synchronize(argv[1]);
    storage_set_setting_text("sync_server_url", argv[1]);
    storage_set_sync_enabled(1);
    assert(sync_client_register_alias(argv[1], alias) == SYNC_OK);
    char list_id[37] = {0}, item_id[37] = {0};
    assert(storage_elist_create_list("Travel", list_id));
    assert(storage_elist_create_item(list_id, "Pack bag", "Passport", item_id));
    synchronize(argv[1]);
    open_client(b);
    assert(sync_account_save(&account, 0) == SYNC_ACCOUNT_SAVE_OK);
    synchronize(argv[1]);
    assert(storage_get_setting_text("sync_account_alias") != NULL);
    assert(strcmp(storage_get_setting_text("sync_account_alias"), alias) == 0);
    assert(storage_session_count() == 1);
    expect_habit(habit_id, habit_name, habit_date);
    expect_list(list_id, item_id, "Travel", "Passport", 0);
    assert(storage_elist_update_item(item_id, "Pack bag", "Passport", 1, 0));
    synchronize(argv[1]);
    open_client(a);
    synchronize(argv[1]);
    expect_list(list_id, item_id, "Travel", "Passport", 1);
    open_client(b);
    assert(storage_load_session_checkin(id, &loaded) && loaded.mood_after == 4);
    checkin.mood_after = 2;
    assert(storage_save_session_checkin(id, &checkin));
    synchronize(argv[1]);
    open_client(a);
    synchronize(argv[1]);
    assert(storage_load_session_checkin(id, &loaded) && loaded.mood_after == 2);
    synchronize(argv[1]);
    assert(storage_session_count() == 1); /* Retrying an acknowledged upload is idempotent. */
    /* Both clients edit offline; A's second edit has the newer logical timestamp. */
    open_client(b);
    checkin.mood_after = 1;
    assert(storage_save_session_checkin(id, &checkin));
    open_client(a);
    checkin.mood_after = 3;
    assert(storage_save_session_checkin(id, &checkin));
    checkin.mood_after = 4;
    assert(storage_save_session_checkin(id, &checkin));
    open_client(b);
    synchronize(argv[1]);
    open_client(a);
    synchronize(argv[1]);
    open_client(b);
    synchronize(argv[1]);
    assert(storage_load_session_checkin(id, &loaded) && loaded.mood_after == 4);
    /* Restore the same key on a fresh device and recover server friendships. */
    SyncAccount friend_account = {0}, restored_account = {0};
    char friend_root[1024], key_path[1024], requests[8192], friends[8192], request_id[128];
    snprintf(friend_root, sizeof(friend_root), "%s/friend", argv[2]);
    snprintf(key_path, sizeof(key_path), "%s/account.key", argv[2]);
    char key_text[SYNC_ACCOUNT_EXPORT_TEXT_SIZE];
    assert(ExportSyncAccountText(&account, key_text, sizeof(key_text)));
    size_t key_size = strlen(key_text);
    FILE *key_file = fopen(key_path, "wb");
    assert(key_file != NULL);
    assert(fwrite(key_text, 1, (size_t)key_size, key_file) == (size_t)key_size);
    assert(fclose(key_file) == 0);
    storage_set_setting_text("sync_server_url", argv[1]);
    storage_set_sync_enabled(1);
    open_client(friend_root);
    assert(sync_account_generate(&friend_account));
    assert(sync_account_save(&friend_account, 0) == SYNC_ACCOUNT_SAVE_OK);
    storage_set_setting_text("sync_server_url", argv[1]);
    storage_set_sync_enabled(1);
    synchronize(argv[1]);
    assert(sync_client_register_alias(argv[1], friend_alias) == SYNC_OK);
    assert(sync_client_send_friend_request(argv[1], account.public_id) == SYNC_OK);
    open_client(b);
    assert(sync_client_get_friend_requests(argv[1], requests, sizeof(requests)) == SYNC_OK);
    assert(storage_json_array_object_text(requests, "$.incoming", 0, "id", request_id, sizeof(request_id)));
    assert(sync_client_accept_friend_request(argv[1], request_id) == SYNC_OK);
    if(moto_setup) {
        char moto_root[1024];
        SyncAccount moto_account = {0};
        snprintf(moto_root, sizeof(moto_root), "%s/moto_seed", argv[2]);
        open_client(moto_root);
        assert(sync_account_import_private_key_preview(&moto_account, key_path));
        assert(sync_account_save(&moto_account, 0) == SYNC_ACCOUNT_SAVE_OK);
        storage_set_setting_text("sync_server_url", argv[1]);
        storage_set_sync_enabled(1);
        storage_close();
        printf("MOTO_SEED %s/inbe.db\n", moto_root);
        return 0;
    }
    open_client(restored);
    assert(sync_account_import_private_key_preview(&restored_account, key_path));
    assert(strcmp(restored_account.public_id, account.public_id) == 0);
    assert(sync_account_save(&restored_account, 0) == SYNC_ACCOUNT_SAVE_OK);
    storage_set_setting_text("sync_server_url", argv[1]);
    storage_set_sync_enabled(1);
    synchronize(argv[1]);
    assert(storage_get_setting_text("sync_account_alias") != NULL);
    assert(strcmp(storage_get_setting_text("sync_account_alias"), alias) == 0);
    assert(sync_client_get_friends(argv[1], friends, sizeof(friends)) == SYNC_OK);
    assert(strstr(friends, friend_account.public_id) != NULL);
    assert(storage_session_count() == 1);
    assert(storage_load_session_checkin(id, &loaded) && loaded.mood_after == 4);
    expect_habit(habit_id, habit_name, habit_date);
    expect_list(list_id, item_id, "Travel", "Passport", 1);
    /* A newly installed app may seed defaults before the key is restored. */
    char restored_defaults[1024];
    SyncAccount default_account = {0};
    snprintf(restored_defaults, sizeof(restored_defaults), "%s/restored_defaults", argv[2]);
    open_client(restored_defaults);
    seed_default_habits();
    assert(sync_account_import_private_key_preview(&default_account, key_path));
    assert(sync_account_save(&default_account, 0) == SYNC_ACCOUNT_SAVE_OK);
    storage_set_setting_text("sync_server_url", argv[1]);
    storage_set_sync_enabled(1);
    synchronize(argv[1]);
    assert(strcmp(storage_get_setting_text("sync_account_alias"), alias) == 0);
    assert(storage_session_count() == 1);
    expect_habit(habit_id, habit_name, habit_date);
    expect_list(list_id, item_id, "Travel", "Passport", 1);
    assert(sync_client_get_friends(argv[1], friends, sizeof(friends)) == SYNC_OK);
    assert(strstr(friends, friend_account.public_id) != NULL);
    open_client(b);
    assert(storage_export_zip(backup));
    open_client(restored);
    assert(storage_import_zip(backup));
    assert(storage_session_count() == 1);
    assert(storage_load_session_checkin(id, &loaded) && loaded.mood_after == 4);
    open_client(b);
    duration = 90;
    assert(storage_save_session_for_activity(&duration, 1, 0, 1, other_id, sizeof(other_id)));
    assert(storage_delete_session(id));
    synchronize(argv[1]);
    open_client(a);
    synchronize(argv[1]);
    assert(storage_session_count() == 1); /* Deletion must preserve the unrelated upload. */
    assert(storage_load_session_checkin(other_id, &loaded));
    assert(storage_delete_session(other_id));
    synchronize(argv[1]);
    open_client(b);
    synchronize(argv[1]);
    assert(storage_session_count() == 0);
    if(live) {
        open_client(restored);
        assert(sync_client_delete_account(argv[1]) == SYNC_OK);
        open_client(friend_root);
        assert(sync_client_delete_account(argv[1]) == SYNC_OK);
    }
    storage_close();
    puts("PASS two-client sync, habit/session/list/alias/friend recovery, offline retry, conflict, backup restore, deletion");
    return 0;
}
