#include "screens/elist_screen.h"
#include "module_host.h"
#include "lists_visibility.h"
#include "diary_types.h"

#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static int save_succeeds = 1;
static int sync_calls;
static int saved_done;
static char saved_comment[ELIST_COMMENT_SIZE];

/* The Lists fixture must never invoke another app's private file effects. */
DiaryFileResult
diary_store_DiaryStoreRead(String name)
{
    (void)name;
    assert(!"Lists requested Diary read access");
    return (DiaryFileResult){0};
}

bool
diary_store_DiaryStoreSave(String name, String data)
{
    (void)name;
    (void)data;
    assert(!"Lists requested Diary write access");
    return false;
}

String
diary_store_DiaryStoreClock(void)
{
    assert(!"Lists requested Diary clock access");
    return StringLiteral("");
}

String
diary_store_DiaryStorePreview(String name)
{
    (void)name;
    assert(!"Lists requested Diary preview access");
    return StringLiteral("");
}

String
diary_store_DiaryImageFormat(String data)
{
    (void)data;
    assert(!"Lists requested Diary image access");
    return StringLiteral("");
}

void
diary_store_DiaryStoreClose(void)
{
    /* Closing the shared module host is allowed; no Diary was opened. */
}


int32_t
AppScale(int32_t pixels)
{
    return pixels;
}

int32_t
app_auto_sync(InnerBreeze *app)
{
    (void)app;
    sync_calls++;
    return 1;
}

int32_t
storage_elist_load(void *value)
{
    EListState *state = value;
    state->list_count = 2;
    memcpy(state->lists[0].id, "old-list", 9);
    memcpy(state->lists[1].id, "created-list", 13);
    if(state->item_count > 0) {
        state->items[0].done = saved_done;
    }
    return 1;
}

int32_t
storage_elist_create_list(String title, uint8_t *out_id)
{
    assert(StringEqual(title, StringView("Shopping", 8)));
    if(save_succeeds)
        memcpy(out_id, "created-list", 13);
    return save_succeeds;
}

int32_t
storage_elist_update_list(String id, String title, int32_t order)
{
    (void)id;
    (void)title;
    (void)order;
    return save_succeeds;
}

int32_t
storage_elist_create_item(String list_id, String title, String comment,
                          uint8_t *out_id)
{
    (void)list_id;
    (void)title;
    (void)out_id;
    assert(comment.length < sizeof(saved_comment));
    memcpy(saved_comment, comment.data, comment.length);
    saved_comment[comment.length] = 0;
    return save_succeeds;
}

int32_t
storage_elist_update_item(String id, String title, String comment,
                          int32_t done, int32_t order)
{
    (void)id;
    (void)title;
    (void)order;
    assert(comment.length < sizeof(saved_comment));
    memcpy(saved_comment, comment.data, comment.length);
    saved_comment[comment.length] = 0;
    if(save_succeeds) {
        saved_done = done;
    }
    return save_succeeds;
}

static void assert_visible(EListState *state, double now, bool expected)
{
    /* The fixture edits records directly, so invalidate the VM result cache. */
    state->visibility_valid = false;
    assert(ListsRefreshVisibility(state, now));
    assert(state->item_visibility[0] == expected);
}

static ListsMutationResult persist_fixture_mutation(void *context, ListsMutation mutation)
{
    (void)context;
    static uint8_t created[37];
    ListsMutationResult result = {0};
    if(mutation.kind == LISTS_CREATE_LIST) {
        result.saved = storage_elist_create_list(mutation.title, created) != 0;
        result.created_id = StringView((char *)created, strlen((char *)created));
    } else if(mutation.kind == LISTS_UPDATE_LIST) {
        result.saved = storage_elist_update_list(mutation.id, mutation.title, mutation.sort_order) != 0;
    } else if(mutation.kind == LISTS_CREATE_ITEM) {
        result.saved = storage_elist_create_item(mutation.parent_id, mutation.title, mutation.comment, NULL) != 0;
    } else if(mutation.kind == LISTS_UPDATE_ITEM) {
        result.saved = storage_elist_update_item(mutation.id, mutation.title, mutation.comment,
                                                mutation.done, mutation.sort_order) != 0;
    } else {
        assert(0);
    }
    return result;
}

int
main(int argc, char **argv)
{
    assert(argc == 2);
    FILE *file = fopen(argv[1], "rb");
    assert(file != NULL && fseek(file, 0, SEEK_END) == 0);
    long size = ftell(file);
    assert(size > 0 && fseek(file, 0, SEEK_SET) == 0);
    char *bytes = malloc((size_t)size);
    assert(bytes != NULL && fread(bytes, 1, (size_t)size, file) == (size_t)size);
    fclose(file);
    CellsBindPersistence((ListsPersist){.call = persist_fixture_mutation},
                          (HabitNameExists){0}, (HabitSave){0});
    assert(CellsOpenPackage(StringView(bytes, (size_t)size)));

    EListState state = {0};
    state.list_count = 1;
    state.item_count = 1;
    state.selected_list = 0;
    memcpy(state.lists[0].id, "list-id", 8);
    memcpy(state.items[0].list_id, "list-id", 8);
    memcpy(state.items[0].id, "item-id", 8);

    assert(elist_screen_elist_ids_equal(state.lists[0].id,
                                       state.items[0].list_id));
    assert(!elist_screen_elist_ids_equal(state.lists[0].id,
                                        state.items[0].id));
    assert_visible(&state, 9.0, true);

    state.items[0].done = 1;
    assert_visible(&state, 9.0, false);
    memcpy(state.completing_item, "item-id", 8);
    state.completing_until = 10.0;
    assert_visible(&state, 9.0, true);
    assert_visible(&state, 10.0, false);

    state.show_completed = 1;
    assert_visible(&state, 11.0, true);
    memcpy(state.items[0].list_id, "other-id", 9);
    assert_visible(&state, 9.0, false);
    state.selected_list = 2;
    assert_visible(&state, 9.0, false);
    state.selected_list = 0;

    static InnerBreeze app;
    app.ui.view_width = 768;
    app.ui.view_height = 720;
    Rectangle bounds = elist_screen_elist_content_bounds(&app);
    assert(bounds.x == 16 && bounds.width == 736);
    app.ui.view_width = 360;
    bounds = elist_screen_elist_content_bounds(&app);
    assert(bounds.x == 16 && bounds.width == 328);

    elist_screen_elist_begin_input(&app, -2, StringView("Shopping", 8));
    assert(app.elist.input_focused && app.elist.input_cursor == 8);
    save_succeeds = 0;
    elist_screen_elist_commit_input(&app);
    assert(app.elist.input_error && app.elist.editing_item == -2);
    assert(strcmp((const char *)app.elist.input, "Shopping") == 0);
    assert(sync_calls == 0);
    save_succeeds = 1;
    elist_screen_elist_commit_input(&app);
    assert(!app.elist.input_error && app.elist.editing_item == -1);
    assert(app.elist.input[0] == 0 && app.elist.selected_list == 1);
    assert(sync_calls == 1);

    elist_screen_elist_begin_input(&app, 0, StringView("Editing task", 12));
    elist_screen_elist_select_list(&app, -1);
    assert(app.elist.selected_list == 1 && app.elist.editing_item == 0);
    elist_screen_elist_select_list(&app, 1);
    assert(strcmp((const char *)app.elist.input, "Editing task") == 0);
    elist_screen_elist_select_list(&app, 0);
    assert(app.elist.selected_list == 0 && app.elist.editing_item == -1);
    assert(app.elist.input[0] == 0 && !app.elist.input_focused);
    assert(sync_calls == 1);

    app.elist.item_count = 1;
    memcpy(app.elist.items[0].comment, "Saved note", 11);
    elist_screen_elist_begin_input(&app, 0, StringView("Renamed task", 12));
    elist_screen_elist_commit_input(&app);
    assert(strcmp(saved_comment, "Saved note") == 0);
    elist_screen_elist_begin_input(&app, -1, StringView("New task", 8));
    elist_screen_elist_commit_input(&app);
    assert(saved_comment[0] == 0);

    app.elist.item_count = 1;
    app.elist.selected_list = 0;
    memcpy(app.elist.items[0].id, "task", 5);
    memcpy(app.elist.items[0].list_id, "old-list", 9);
    assert_visible(&app.elist, 10.0, true);
    int before_sync = sync_calls;
    save_succeeds = 0;
    assert(!elist_screen_elist_set_done(&app, 0, 1, 10.0));
    assert(!app.elist.items[0].done && sync_calls == before_sync);
    save_succeeds = 1;
    assert(elist_screen_elist_set_done(&app, 0, 1, 10.0));
    assert(app.elist.items[0].done && sync_calls == before_sync + 1);
    assert_visible(&app.elist, 10.2, true);
    assert_visible(&app.elist, 10.5, false);
    app.elist.show_completed = 1;
    assert_visible(&app.elist, 11.0, true);
    assert(elist_screen_elist_set_done(&app, 0, 0, 11.0));
    app.elist.show_completed = 0;
    assert_visible(&app.elist, 12.0, true);
    app.elist.show_completed = 1;
    elist_screen_elist_select_list(&app, 1);
    assert(!app.elist.show_completed);
    assert_visible(&app.elist, 12.0, false);
    CellsClose();
    free(bytes);
    return 0;
}
