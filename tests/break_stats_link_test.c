#include "storage/break_stats.h"
/* The generated SQLite module and the vendor header define the same
 * constants; the vendor definitions win here. */
#undef SQLITE_OK
#undef SQLITE_ROW
#undef SQLITE_DONE
#undef SQLITE_BUSY
#undef SQLITE_TRANSIENT
#undef SQLITE_LOCKED
#undef SQLITE_NOMEM
#undef SQLITE_TOOBIG
#undef SQLITE_MISUSE
#undef SQLITE_OPEN_READWRITE
#undef SQLITE_OPEN_CREATE
#undef SQLITE_OPEN_FULLMUTEX
#include <sqlite3.h>

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static LocalDateTime forced_local;
static bool use_forced_local;

LocalDateTime
LocalNowHost(void)
{
    if (use_forced_local) {
        return forced_local;
    }
    time_t now = time(NULL);
    struct tm *local = localtime(&now);
    LocalDateTime result = {0};

    assert(local != NULL);
    result.year = local->tm_year + 1900;
    result.month = local->tm_mon + 1;
    result.day = local->tm_mday;
    result.day_of_year = local->tm_yday;
    result.hour = local->tm_hour;
    result.minute = local->tm_min;
    result.second = local->tm_sec;
    result.valid = true;
    return result;
}

int64_t
UnixNowHost(void)
{
    return 1234567890;
}

static int
date_ago(int days)
{
    struct tm local = {0};
    local.tm_year = 2026 - 1900;
    local.tm_mon = 0;
    local.tm_mday = 1;
    local.tm_hour = 12;
    local.tm_mday -= days;
    assert(mktime(&local) != (time_t)-1);
    return (local.tm_year + 1900) * 10000 +
           (local.tm_mon + 1) * 100 + local.tm_mday;
}

static void
insert_row(const char *user, int date, int prompts)
{
    static const char sql[] =
        "INSERT INTO break_days(user_id,local_date,break_type,prompts,"
        "updated_at) VALUES(?,?,?,?,0)";
    sqlite3_stmt *stmt = NULL;

    assert(sqlite3_prepare_v2(storage_state_handle()->db, sql, -1,
                              &stmt, NULL) == SQLITE_OK);
    assert(sqlite3_bind_text(stmt, 1, user, -1, SQLITE_TRANSIENT) == SQLITE_OK);
    assert(sqlite3_bind_int(stmt, 2, date) == SQLITE_OK);
    assert(sqlite3_bind_int(stmt, 3, BREAK_MICRO) == SQLITE_OK);
    assert(sqlite3_bind_int(stmt, 4, prompts) == SQLITE_OK);
    assert(sqlite3_step(stmt) == SQLITE_DONE);
    assert(sqlite3_finalize(stmt) == SQLITE_OK);
}

int
main(void)
{
    static const char schema[] =
        "CREATE TABLE break_days("
        "user_id TEXT NOT NULL, local_date INTEGER NOT NULL,"
        "break_type INTEGER NOT NULL, prompts INTEGER NOT NULL DEFAULT 0,"
        "repeated_prompts INTEGER NOT NULL DEFAULT 0,"
        "taken INTEGER NOT NULL DEFAULT 0,"
        "natural INTEGER NOT NULL DEFAULT 0,"
        "skipped INTEGER NOT NULL DEFAULT 0,"
        "postponed INTEGER NOT NULL DEFAULT 0,"
        "overdue_s INTEGER NOT NULL DEFAULT 0,"
        "usage_s INTEGER NOT NULL DEFAULT 0,"
        "updated_at INTEGER NOT NULL,"
        "PRIMARY KEY(user_id,local_date,break_type))";
    BreakEngine engine = {0};
    BreakDayRow rows[8] = {{0}};
    int count;
    int today = date_ago(0);
    StorageState *state = storage_state_handle();
    sqlite3 *database = NULL;

    forced_local = (LocalDateTime){0};
    forced_local.valid = true;
    forced_local.year = 2026;
    forced_local.month = 1;
    forced_local.day = 1;
    forced_local.hour = 12;
    use_forced_local = true;

    assert(sqlite3_open(":memory:", &database) == SQLITE_OK);
    state->db = database;
    assert(sqlite3_exec(database, schema, NULL, NULL, NULL) == SQLITE_OK);
    strcpy((char *)state->user_id, "local-user");
    assert(storage_break_today() == today);
    {
        LocalDateTime local = {0};
        local.valid = true;
        local.year = 2026;
        local.month = 1;
        local.day = 1;
        local.hour = 3;
        assert(BreakServiceDate(local) == 20251231);
        local.hour = 4;
        assert(BreakServiceDate(local) == 20260101);
        assert(BreakDayFromStoredKey(2025 * 366 + 365) == 20251231);
        assert(BreakDayFromStoredKey(740101) == 20220219);
        assert(BreakDayFromStoredKey(20260101) == 20260101);
    }
    assert(BreakHistoryCutoff(20260301, 7) == 20260223);
    assert(BreakHistoryCutoff(20240301, 2) == 20240229);
    assert(BreakHistoryCutoff(20230301, 2) == 20230228);
    assert(BreakHistoryCutoff(20260301, 0) == 20260301);
    assert(BreakHistoryCutoff(20260230, 7) == 0);

    engine.stats[BREAK_MICRO].prompts = 4;
    engine.stats[BREAK_MICRO].repeated_prompts = 2;
    engine.stats[BREAK_MICRO].taken = 3;
    engine.stats[BREAK_REST].skipped = 1;
    engine.stats[BREAK_DAILY].overdue_s = 85;
    engine.usage_today_s = 900;
    storage_break_flush_day(&engine);
    count = storage_break_history(0, rows, 8);
    assert(count == BREAK_TYPE_COUNT);
    assert(rows[0].local_date == today);
    assert(rows[0].break_type == BREAK_MICRO);
    assert(rows[0].prompts == 4);
    assert(rows[0].repeated_prompts == 2);
    assert(rows[0].taken == 3);
    assert(rows[0].usage_s == 900);
    assert(rows[1].skipped == 1);
    assert(rows[2].overdue_s == 85);

    engine.stats[BREAK_MICRO].prompts = 5;
    storage_break_flush_day(&engine);
    assert(storage_break_history(0, rows, 8) == BREAK_TYPE_COUNT);
    assert(rows[0].prompts == 5);

    insert_row("local-user", date_ago(6), 60);
    insert_row("local-user", date_ago(7), 70);
    insert_row("local-user", date_ago(8), 80);
    insert_row("foreign-user", today, 99);
    count = storage_break_history(7, rows, 8);
    assert(count == BREAK_TYPE_COUNT + 1);
    assert(rows[3].local_date == date_ago(6) && rows[3].prompts == 60);
    assert(storage_break_history(7, rows, 2) == 2);
    assert(storage_break_history(7, NULL, 8) == 0);
    assert(storage_break_history(-1, rows, 8) == 0);

    strcpy((char *)state->user_id, "foreign-user");
    assert(storage_break_history(0, rows, 8) == 1);
    assert(rows[0].prompts == 99);

    strcpy((char *)state->user_id, "rollover-user");
    forced_local = (LocalDateTime){0};
    forced_local.valid = true;
    forced_local.year = 2026;
    forced_local.month = 1;
    forced_local.day = 1;
    forced_local.hour = 3;
    use_forced_local = true;
    storage_break_flush_day(&engine);
    use_forced_local = false;
    {
        sqlite3_stmt *stmt = NULL;
        const char *sql = "SELECT COUNT(*) FROM break_days WHERE user_id = ? "
                          "AND local_date = ?";
        assert(sqlite3_prepare_v2(database, sql, -1, &stmt, NULL) == SQLITE_OK);
        assert(sqlite3_bind_text(stmt, 1, (char *)state->user_id, -1,
                                SQLITE_TRANSIENT) == SQLITE_OK);
        assert(sqlite3_bind_int(stmt, 2, 20251231) == SQLITE_OK);
        assert(sqlite3_step(stmt) == SQLITE_ROW);
        assert(sqlite3_column_int(stmt, 0) == BREAK_TYPE_COUNT);
        assert(sqlite3_finalize(stmt) == SQLITE_OK);
    }
    assert(sqlite3_close(database) == SQLITE_OK);
    puts("break stats Ziran and SQLite passed");
    return 0;
}
