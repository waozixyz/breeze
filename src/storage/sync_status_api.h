#ifndef INBE_STORAGE_SYNC_STATUS_API_H
#define INBE_STORAGE_SYNC_STATUS_API_H

typedef struct StorageSyncStatus {
    int has_account;
    int enabled;
    int review_pending;
    int repair_pending;
    int full_upload_done;
    long long server_version;
    long long server_clock;
    long long queued_changes;
} StorageSyncStatus;

int storage_sync_status(StorageSyncStatus *status);

#endif
