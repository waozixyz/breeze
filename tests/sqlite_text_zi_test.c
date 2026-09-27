#include "zir_string.h"

#include <assert.h>
#include <sqlite3.h>
#include <stdio.h>
#include <string.h>

int32_t SqlitePrepareText(void *db, String sql, int32_t length,
                          void **statement, uint8_t **tail);
int32_t SqliteBindTextString(void *statement, int32_t index,
                             String value, int32_t length);
int32_t SqliteStep(void *statement);
int32_t SqliteFinalize(void *statement);
int32_t SqliteExecText(void *database, String sql);

int
main(void)
{
    sqlite3 *db = NULL;
    void *statement = NULL;
    assert(sqlite3_open(":memory:", &db) == SQLITE_OK);

    char query[6001];
    memcpy(query, "SELECT ?1", 9);
    memset(query + 9, ' ', 5991);
    query[6000] = 0;
    assert(SqlitePrepareText(db, StringView(query, 6000), -1,
                             &statement, NULL) == SQLITE_OK);

    char text[10001];
    memset(text, 'x', 10000);
    text[10000] = 0;
    assert(SqliteBindTextString(statement, 1, StringView(text, 10000),
                                10000) == SQLITE_OK);
    memset(text, 'y', 10000);
    assert(SqliteStep(statement) == SQLITE_ROW);
    assert(sqlite3_column_bytes((sqlite3_stmt *)statement, 0) == 10000);
    const unsigned char *bound = sqlite3_column_text((sqlite3_stmt *)statement, 0);
    assert(bound[0] == 'x' && bound[9999] == 'x');
    assert(SqliteFinalize(statement) == SQLITE_OK);

    statement = NULL;
    assert(SqlitePrepareText(db, StringView("SELECT ?1", 9), -1,
                             &statement, NULL) == SQLITE_OK);
    char binary[] = {'a', 0, 'b'};
    assert(SqliteBindTextString(statement, 1, StringView(binary, 3), 3) == SQLITE_OK);
    binary[0] = 'z';
    assert(SqliteStep(statement) == SQLITE_ROW);
    assert(sqlite3_column_bytes((sqlite3_stmt *)statement, 0) == 3);
    bound = sqlite3_column_text((sqlite3_stmt *)statement, 0);
    assert(bound[0] == 'a' && bound[1] == 0 && bound[2] == 'b');
    assert(SqliteFinalize(statement) == SQLITE_OK);

    char long_sql[6001];
    memcpy(long_sql, "CREATE TABLE test(value INTEGER);", 33);
    memset(long_sql + 33, ' ', 5967);
    long_sql[6000] = 0;
    assert(SqliteExecText(db, StringView(long_sql, 6000)) == SQLITE_OK);
    assert(sqlite3_exec(db, "INSERT INTO test VALUES(7)", NULL, NULL, NULL) == SQLITE_OK);

    assert(sqlite3_close(db) == SQLITE_OK);
    puts("Ziran SQLite text preserves long and binary values after binding");
    return 0;
}
