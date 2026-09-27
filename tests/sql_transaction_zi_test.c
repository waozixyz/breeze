#define _POSIX_C_SOURCE 200809L
#include "zir_string.h"

#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <sqlite3.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

int32_t SqliteExecTransaction(void *database, String sql);

struct Worker {
    sqlite3 *database;
    atomic_int started;
    atomic_int finished;
};

static void *
query_worker(void *argument)
{
    struct Worker *worker = argument;
    atomic_store(&worker->started, 1);
    assert(SqliteExecTransaction(worker->database, StringView("SELECT 1", 8)) == 1);
    atomic_store(&worker->finished, 1);
    return NULL;
}

static void
assert_blocked_until_finished(sqlite3 *database, const char *finish_sql)
{
    struct Worker worker = {.database = database};
    pthread_t thread;
    assert(pthread_create(&thread, NULL, query_worker, &worker) == 0);
    while (!atomic_load(&worker.started)) {
        sched_yield();
    }
    const struct timespec delay = {.tv_nsec = 100000000};
    nanosleep(&delay, NULL);
    assert(atomic_load(&worker.finished) == 0);
    assert(SqliteExecTransaction(database, StringView(finish_sql, strlen(finish_sql))) == 1);
    assert(pthread_join(thread, NULL) == 0);
    assert(atomic_load(&worker.finished) == 1);
}

int
main(void)
{
    sqlite3 *database = NULL;
    assert(sqlite3_open_v2(":memory:", &database,
                           SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX,
                           NULL) == SQLITE_OK);
    assert(SqliteExecTransaction(database, StringView("CREATE TABLE item(n INTEGER)", 28)) == 1);

    assert(SqliteExecTransaction(database, StringView("BEGIN IMMEDIATE", 15)) == 1);
    assert(sqlite3_get_autocommit(database) == 0);
    assert_blocked_until_finished(database, "COMMIT");
    assert(sqlite3_get_autocommit(database) == 1);

    assert(SqliteExecTransaction(database, StringView("BEGIN IMMEDIATE", 15)) == 1);
    assert(SqliteExecTransaction(database, StringView("INSERT INTO missing VALUES(1)", 29)) == 0);
    assert(sqlite3_get_autocommit(database) == 0);
    assert_blocked_until_finished(database, "ROLLBACK");
    assert(sqlite3_get_autocommit(database) == 1);

    assert(SqliteExecTransaction(database, StringView("SAVEPOINT outer", 15)) == 1);
    assert(SqliteExecTransaction(database, StringView("SAVEPOINT inner", 15)) == 1);
    assert(SqliteExecTransaction(database, StringView("RELEASE inner", 13)) == 1);
    assert(sqlite3_get_autocommit(database) == 0);
    assert_blocked_until_finished(database, "RELEASE outer");
    assert(sqlite3_get_autocommit(database) == 1);

    assert(SqliteExecTransaction(database,
                                 StringView("BEGIN; INSERT INTO item VALUES(1); COMMIT;", 42)) == 1);
    assert(sqlite3_get_autocommit(database) == 1);
    assert(SqliteExecTransaction(database, StringView("SELECT 1", 8)) == 1);
    assert(sqlite3_close(database) == SQLITE_OK);
    puts("Ziran SQL transactions retain and release the connection mutex");
    return 0;
}
