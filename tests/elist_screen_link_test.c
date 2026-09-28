#include "screens/elist_screen.h"

#include <assert.h>
#include <string.h>

static int save_succeeds = 1;
static int sync_calls;
static char saved_comment[ELIST_COMMENT_SIZE];


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
    (void)done;
    (void)order;
    assert(comment.length < sizeof(saved_comment));
    memcpy(saved_comment, comment.data, comment.length);
    saved_comment[comment.length] = 0;
    return save_succeeds;
}

int
main(void)
{
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
    assert(elist_screen_elist_item_visible(&state, 0, 9.0));

    state.items[0].done = 1;
    assert(!elist_screen_elist_item_visible(&state, 0, 9.0));
    memcpy(state.completing_item, "item-id", 8);
    state.completing_until = 10.0;
    assert(elist_screen_elist_item_visible(&state, 0, 9.0));
    assert(!elist_screen_elist_item_visible(&state, 0, 10.0));

    state.show_completed = 1;
    assert(elist_screen_elist_item_visible(&state, 0, 11.0));
    memcpy(state.items[0].list_id, "other-id", 9);
    assert(!elist_screen_elist_item_visible(&state, 0, 9.0));
    assert(!elist_screen_elist_item_visible(&state, 1, 9.0));

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
    assert(elist_screen_elist_item_visible(&app.elist, 0, 10.0));
    int before_sync = sync_calls;
    save_succeeds = 0;
    assert(!elist_screen_elist_set_done(&app, 0, 1, 10.0));
    assert(!app.elist.items[0].done && sync_calls == before_sync);
    save_succeeds = 1;
    assert(elist_screen_elist_set_done(&app, 0, 1, 10.0));
    assert(app.elist.items[0].done && sync_calls == before_sync + 1);
    assert(elist_screen_elist_item_visible(&app.elist, 0, 10.2));
    assert(!elist_screen_elist_item_visible(&app.elist, 0, 10.5));
    app.elist.show_completed = 1;
    assert(elist_screen_elist_item_visible(&app.elist, 0, 11.0));
    assert(elist_screen_elist_set_done(&app, 0, 0, 11.0));
    app.elist.show_completed = 0;
    assert(elist_screen_elist_item_visible(&app.elist, 0, 12.0));
    app.elist.show_completed = 1;
    elist_screen_elist_select_list(&app, 1);
    assert(!app.elist.show_completed);
    assert(!elist_screen_elist_item_visible(&app.elist, 0, 12.0));
    return 0;
}
