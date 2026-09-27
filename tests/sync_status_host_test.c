#include "sync_status_link_behavior.h"
#include "sync_status_api.h"

#include <assert.h>

static int fail_read;

int
storage_sync_status(StorageSyncStatus *status)
{
    if(fail_read)
        return 0;
    *status = (StorageSyncStatus){0};
    status->has_account = 1;
    status->enabled = 1;
    status->review_pending = 1;
    status->server_clock = 4294967297LL;
    status->queued_changes = 4294967298LL;
    return 1;
}

int
main(void)
{
    assert(Answer() == 42);
    fail_read = 1;
    assert(FailureClearsStatus());
    return 0;
}
