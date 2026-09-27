#include "sqlite3.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static sqlite3 *database;
static char current_user_id[64];
static char current_meta_text[8192];

int32_t schema_create(void);
int32_t migrate_schema(void);
int64_t db_select_int64(uint8_t *sql, int64_t fallback);
int32_t db_select_int(uint8_t *sql, int32_t fallback);
int32_t db_exec_text(uint8_t *sql, uint8_t *text);
int32_t load_or_create_user(void);
int32_t meta_equals(uint8_t *key, uint8_t *value);
uint8_t *get_meta_text(uint8_t *key);
void set_meta(uint8_t *key, uint8_t *value);
int64_t get_meta_int64(uint8_t *key, int64_t fallback);
void set_meta_int64(uint8_t *key, int64_t value);

void *storage_db_handle(void) { return database; }
char *storage_user_id_buffer(void) { return current_user_id; }
char *storage_meta_text_buffer(void) { return current_meta_text; }

int32_t exec_sql(uint8_t *sql)
{
    char *error = NULL;
    int result = sqlite3_exec(database, (const char *)sql, NULL, NULL, &error);
    if(result != SQLITE_OK)
        fprintf(stderr, "schema SQL failed: %s\n",
                error != NULL ? error : (const char *)sql);
    sqlite3_free(error);
    return result == SQLITE_OK;
}

int32_t table_has_column(uint8_t *table, uint8_t *column)
{
    char sql[128];
    sqlite3_stmt *statement = NULL;
    int found = 0;

    snprintf(sql, sizeof sql, "PRAGMA table_info(%s)", (const char *)table);
    assert(sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK);
    while(sqlite3_step(statement) == SQLITE_ROW) {
        const char *name = (const char *)sqlite3_column_text(statement, 1);
        if(name != NULL && strcmp(name, (const char *)column) == 0) {
            found = 1;
            break;
        }
    }
    sqlite3_finalize(statement);
    return found;
}

int32_t table_exists(uint8_t *table)
{
    sqlite3_stmt *statement = NULL;
    int found;

    assert(sqlite3_prepare_v2(database,
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1",
        -1, &statement, NULL) == SQLITE_OK);
    sqlite3_bind_text(statement, 1, (const char *)table, -1, SQLITE_STATIC);
    found = sqlite3_step(statement) == SQLITE_ROW;
    sqlite3_finalize(statement);
    return found;
}

int64_t now_seconds(void) { return 1770000000LL; }
int app_web_platform(void) { return 0; }

static long long scalar(const char *sql)
{
    sqlite3_stmt *statement = NULL;
    long long value;
    assert(sqlite3_prepare_v2(database, sql, -1, &statement, NULL) == SQLITE_OK);
    assert(sqlite3_step(statement) == SQLITE_ROW);
    value = sqlite3_column_int64(statement, 0);
    sqlite3_finalize(statement);
    return value;
}

static int has_table(const char *name)
{
    return table_exists((uint8_t *)name);
}

static int has_column(const char *table, const char *column)
{
    return table_has_column((uint8_t *)table, (uint8_t *)column);
}

static void open_memory_database(void)
{
    assert(sqlite3_open(":memory:", &database) == SQLITE_OK);
    memset(current_user_id, 0, sizeof current_user_id);
}

static void close_database(void)
{
    assert(sqlite3_close(database) == SQLITE_OK);
    database = NULL;
}

int main(void)
{
    open_memory_database();
    assert(schema_create());
    assert(!has_table("sync_outbox"));
    assert(migrate_schema());
    assert(has_table("sync_outbox"));
    assert(has_column("habits", "reminder_hour"));
    assert(has_column("sessions", "mood_after"));
    assert(scalar("SELECT value FROM meta WHERE key='schema_version'") == 1);
    assert(db_select_int64((uint8_t *)"SELECT 42", -1) == 42);
    assert(db_select_int((uint8_t *)"SELECT 7", -1) == 7);
    assert(db_select_int64((uint8_t *)"SELECT value FROM meta WHERE key='missing'", 19) == 19);
    assert(db_exec_text((uint8_t *)
        "INSERT INTO meta(key,value) VALUES('query_test',?1)",
        (uint8_t *)"stored"));
    assert(scalar("SELECT COUNT(*) FROM meta WHERE key='query_test' AND value='stored'") == 1);
    assert(meta_equals((uint8_t *)"query_test", (uint8_t *)"stored"));
    assert(!meta_equals((uint8_t *)"query_test", (uint8_t *)"other"));
    assert(strcmp((char *)get_meta_text((uint8_t *)"query_test"), "stored") == 0);
    assert(get_meta_text((uint8_t *)"missing") == NULL);
    set_meta((uint8_t *)"query_test", (uint8_t *)"updated");
    assert(strcmp((char *)get_meta_text((uint8_t *)"query_test"), "updated") == 0);
    set_meta((uint8_t *)"empty", (uint8_t *)"");
    assert(get_meta_text((uint8_t *)"empty") == NULL);
    set_meta((uint8_t *)"null_value", NULL);
    assert(scalar("SELECT COUNT(*) FROM meta WHERE key='null_value' AND value=''") == 1);
    assert(get_meta_int64((uint8_t *)"missing", 12) == 12);
    set_meta_int64((uint8_t *)"min", INT64_MIN);
    assert(get_meta_int64((uint8_t *)"min", 0) == INT64_MIN);
    set_meta_int64((uint8_t *)"max", INT64_MAX);
    assert(get_meta_int64((uint8_t *)"max", 0) == INT64_MAX);
    set_meta_int64((uint8_t *)"min", 0);
    assert(get_meta_int64((uint8_t *)"min", 12) == 0);
    assert(load_or_create_user());
    assert(strncmp(current_user_id, "local-1770000000-", 17) == 0);
    assert(scalar("SELECT COUNT(*) FROM users WHERE kind='local'") == 1);
    assert(load_or_create_user());
    assert(scalar("SELECT COUNT(*) FROM users WHERE kind='local'") == 1);
    close_database();

    open_memory_database();
    assert(exec_sql((uint8_t *)
        "CREATE TABLE users(id TEXT PRIMARY KEY,created_at INTEGER,kind TEXT);"
        "INSERT INTO users VALUES('original-user',1,'local');"
        "CREATE TABLE habits(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,"
        "name TEXT NOT NULL,color_r INTEGER NOT NULL,color_g INTEGER NOT NULL,"
        "color_b INTEGER NOT NULL,sync_mode INTEGER NOT NULL,"
        "sync_activity INTEGER NOT NULL,sync_topic INTEGER NOT NULL,"
        "sort_order INTEGER NOT NULL,deleted_at INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO habits VALUES('h1','u1','Practice',1,2,3,1,2,9,0,0);"
        "CREATE TABLE habit_days(habit_id TEXT NOT NULL,local_date INTEGER NOT NULL,"
        "completed INTEGER NOT NULL,updated_at INTEGER NOT NULL,"
        "PRIMARY KEY(habit_id,local_date));"
        "INSERT INTO habit_days VALUES('h1',20260925,1,21);"
        "CREATE TABLE settings(user_id TEXT,key TEXT,value TEXT,updated_at INTEGER,"
        "PRIMARY KEY(user_id,key));"
        "INSERT INTO settings VALUES('u1','language','es',12);"
        "CREATE TABLE sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,"
        "started_at INTEGER NOT NULL,local_date INTEGER NOT NULL,"
        "topic INTEGER NOT NULL,activity INTEGER NOT NULL,source TEXT NOT NULL,"
        "imported_at INTEGER NOT NULL,rounds_hash INTEGER NOT NULL,"
        "UNIQUE(user_id,started_at,rounds_hash));"
        "INSERT INTO sessions VALUES('s1','u1',10,20260925,0,0,'local',10,123);"
        "CREATE TABLE sync_ops(op_id TEXT PRIMARY KEY,payload_json TEXT);"
        "INSERT INTO sync_ops VALUES('old','{}');"
        "CREATE TABLE social_cache(user_id TEXT,kind TEXT,json TEXT,updated_at INTEGER);"
        "INSERT INTO social_cache VALUES('u1','friends','{}',17);"));
    assert(schema_create());
    assert(!has_table("sync_outbox"));
    assert(migrate_schema());
    assert(load_or_create_user());
    assert(strcmp(current_user_id, "original-user") == 0);
    assert(!has_table("habits_with_sync_topic"));
    assert(!has_table("social_cache"));
    assert(has_table("sync_ops"));
    assert(scalar("SELECT COUNT(*) FROM sync_ops WHERE op_id='old'") == 1);
    assert(scalar("SELECT COUNT(*) FROM habits WHERE id='h1' AND name='Practice' ") == 1);
    assert(scalar("SELECT count FROM habit_days WHERE habit_id='h1'") == 1);
    assert(scalar("SELECT COUNT(*) FROM settings WHERE key='language' AND value='es'") == 1);
    assert(scalar("SELECT updated_at FROM sessions WHERE id='s1'") == 1770000000);
    assert(scalar("SELECT COUNT(*) FROM social_snapshots WHERE kind='friends'") == 1);
    assert(scalar("SELECT COUNT(*) FROM sync_outbox") == 3);
    assert(migrate_schema());
    assert(scalar("SELECT COUNT(*) FROM sync_outbox") == 3);
    assert(scalar("SELECT COUNT(*) FROM sync_ops WHERE op_id='old'") == 1);
    close_database();

    open_memory_database();
    assert(exec_sql((uint8_t *)
        "CREATE TABLE sync_ops(op_id TEXT PRIMARY KEY,payload_json TEXT);"
        "INSERT INTO sync_ops VALUES('pending','{}');"
        "CREATE TABLE social_cache(user_id TEXT,kind TEXT,updated_at INTEGER);"
        "INSERT INTO social_cache VALUES('u1','friends',17);"));
    assert(schema_create());
    assert(!migrate_schema());
    assert(has_table("sync_ops"));
    assert(has_table("social_cache"));
    assert(!has_table("sync_outbox"));
    assert(scalar("SELECT COUNT(*) FROM sync_ops") == 1);
    close_database();

    puts("Inbe Ziran schema creation and data upgrade passed");
    return 0;
}
