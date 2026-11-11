#include <sqlite3.h>
#include <stdio.h>
#include <string.h>

static char source_key[79];
void CompressionFailSourceWrite(const char *key)
{
    snprintf(source_key, sizeof source_key, "%s", key ? key : "");
}

int __real_sqlite3_step(sqlite3_stmt *statement);
int __wrap_sqlite3_step(sqlite3_stmt *statement)
{
    const char *sql = sqlite3_sql(statement);
    if (source_key[0] && sql &&
        (strstr(sql, "INTO settings") || strstr(sql, "UPDATE settings"))) {
        char *expanded = sqlite3_expanded_sql(statement);
        int fail = expanded && strstr(expanded, source_key);
        sqlite3_free(expanded);
        if (fail) return SQLITE_IOERR;
    }
    return __real_sqlite3_step(statement);
}

void app_web_storage_flush(void) {}
