#include "sync_result.h"
#include "sync_retry.h"

#include <limits.h>

int
main(void)
{
    RetryDecision retry = sync_retry_decision(SyncResult_SYNC_REQUEST_FAILED, 0);
    RetryDecision stop = sync_retry_decision(SyncResult_SYNC_AUTH_FAILED, INT_MAX);

    return retry.attempt == 1 && retry.delay == 5 && !retry.needs_action &&
        stop.attempt == 4 && stop.delay == 0 && stop.needs_action &&
        app_sync_retry_delay(INT_MIN) == 5.0 ? 0 : 1;
}
