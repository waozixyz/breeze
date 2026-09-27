#include "storage/db.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    assert(storage_state_size() == sizeof(StorageState));
    assert(storage_state_handle() == &g_storage);
    assert(storage_db_handle() == NULL);
    assert(storage_user_id_buffer() == g_storage.user_id);

    g_storage.db = (sqlite3 *)(uintptr_t)0x1234;
    assert(storage_db_handle() == g_storage.db);
    strcpy(g_storage.user_id, "existing-user");
    assert(strcmp(storage_user_id_buffer(), "existing-user") == 0);
    g_storage.materialize_defer = 2;
    g_storage.pending_sync_outbox_seq = INT64_MAX;
    StorageState *state = storage_state_handle();
    assert(state->materialize_defer == 2);
    assert(state->pending_sync_outbox_seq == INT64_MAX);
    char path[32] = "untouched";
    assert(storage_join_path(path, sizeof path, "/tmp/inbe", "inbe.db"));
    assert(strcmp(path, "/tmp/inbe/inbe.db") == 0);
    strcpy(path, "unchanged");
    assert(!storage_join_path(path, 5, "/tmp/inbe", "inbe.db"));
    assert(strcmp(path, "unchanged") == 0);
    assert(!storage_join_path(path, sizeof path, "", "inbe.db"));
    puts("Inbe Ziran storage state ABI passed");
    return 0;
}
