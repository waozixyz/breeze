#include "sync_recovery_behavior.h"
#include "db.h"

#include <stdio.h>
#include <string.h>

/* The storage layer is replaced by two in-memory settings and a queue, so this
   checks only the retry and status decisions in app_sync. */
static double test_time = 100;
static int last_result;
static int retry_attempt;
static int enabled = 1;
static int64_t queued;
static int repair;
static int full_upload;

bool storage_sync_node_failover(void) { return false; }
int32_t app_preview_mode(void) { return 0; }
void TraceLog(int32_t level, const char *format, ...) {}
int64_t sqlite3_total_changes64(void *database) { return 0; }
String storage_get_setting_text(String key) { return StringLiteral("https://sync.example"); }

double
GetTime(void)
{
    return test_time;
}

static int
is_key(String key, const char *name)
{
    return key.length == strlen(name) && memcmp(key.data, name, key.length) == 0;
}

int32_t
storage_get_setting_int(String key, int32_t fallback)
{
    if(is_key(key, "sync_last_result"))
        return last_result;
    if(is_key(key, "sync_retry_attempt"))
        return retry_attempt;
    return fallback;
}

void
storage_set_setting_int(String key, int32_t value)
{
    if(is_key(key, "sync_last_result"))
        last_result = value;
    if(is_key(key, "sync_retry_attempt"))
        retry_attempt = value;
}

int32_t
storage_sync_enabled(void)
{
    return enabled;
}

int32_t
storage_sync_status(StorageSyncStatus *status)
{
    memset(status, 0, sizeof(*status));
    status->has_account = 1;
    status->enabled = enabled;
    status->repair_pending = repair;
    status->full_upload_done = full_upload;
    status->queued_changes = queued;
    return 1;
}

void
recovery_set_time(double seconds)
{
    test_time = seconds;
}

void
recovery_set_enabled(int32_t value)
{
    enabled = value;
    storage_connection_generation++;
}

void
recovery_set_queue(int64_t queued_changes, int32_t repair_pending,
                   int32_t full_upload_done)
{
    queued = queued_changes;
    repair = repair_pending;
    full_upload = full_upload_done;
}

int
main(void)
{
    int failed = Answer();
    if(failed != 0) {
        fprintf(stderr, "sync recovery check %d failed\n", failed);
        return 1;
    }
    return 0;
}
