#include "screens/settings/settings_telegram.h"
#include "lumi_authorization.h"
#include "lumi_telegram.h"
#include "session.h"
#include "tree.h"
#include "tree_input.h"
#include "paint_queue.h"
#include "scroll_device.h"
#include "scroll_widget.h"
#include "text_buffers.h"
#include "metrics.h"
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static bool truncated_review;
enum { ReviewValueCount = 6 };
static const char *const review_values[ReviewValueCount] = {
    "inbe", "123456", "700001", "https://api.waozi.xyz", "private.inbe.v2.lumi", "1791529031"
};
static bool text_equal(String text, const char *expected)
{
    size_t length = strlen(expected);
    return text.length == length && memcmp(text.data, expected, length) == 0;
}
static bool contains(String text, const char *needle)
{
    size_t length = strlen(needle);
    for (size_t offset = 0; offset + length <= text.length; ++offset) {
        if (memcmp(text.data + offset, needle, length) == 0) {
            return true;
        }
    }
    return false;
}
String __wrap_storage_get_setting_text(String key)
{
    if (text_equal(key, "sync_private_key")) {
        return StringView("synthetic-owner-present", 23);
    }
    return StringView("", 0);
}
int32_t __wrap_storage_has_sync_account(void)
{
    return 1;
}
void __wrap_app_apply_nav_route(InnerBreeze *app, int32_t route)
{
    (void)app;
    (void)route;
    assert(0);
}
bool __wrap_lumi_telegram_LumiTelegramOpen(String start)
{
    (void)start;
    assert(0);
    return false;
}
String __wrap_LocaleText(String key)
{
    const char *text = "Ready";
    if (text_equal(key, "lumi_authorization_details")) {
        text = "App: %\nAccount: %\nBot: % · Telegram user: %\nNode: %\nAddress: %\n"
               "Read and write only: %\nRequest expires at (Unix seconds): %";
    } else if (text_equal(key, "lumi_authorization_fingerprints")) {
        text = "Signing key fingerprint: %\nEncryption key fingerprint: %";
    } else if (text_equal(key, "lumi_authorization_approve")) {
        text = "Approve Lumi access for 24 hours";
    } else if (text_equal(key, "lumi_authorization_review")) {
        text = "Compare the account, node and both key fingerprints before approving.";
    } else if (text_equal(key, "lumi_telegram_body")) {
        text = "Continue your Lumi chat in Telegram.";
    } else if (text_equal(key, "cancel_button")) {
        text = "Cancel";
    }
    return StringView(text, strlen(text));
}
String __real_FrameTextHold(FrameTextStore *store, String value);
String __wrap_FrameTextHold(FrameTextStore *store, String value)
{
    if (truncated_review && contains(value, "Signing key fingerprint:")) {
        return __real_FrameTextHold(store, StringView(value.data, value.length - 1));
    }
    return __real_FrameTextHold(store, value);
}
int32_t MeasureGlyphWidth(String text, int32_t font, String face)
{
    (void)face;
    return (int32_t)text.length * font / 2;
}
int32_t MeasureGlyphLineHeight(int32_t font, String face)
{
    (void)face;
    return font;
}
void RasterRoundedRectangle(Rectangle bounds, float radius, int32_t segments, Color color)
{
    (void)bounds;
    (void)radius;
    (void)segments;
    (void)color;
    assert(0);
}
void RasterRoundedRectangleOutline(Rectangle bounds, float radius, int32_t segments, float width, Color color)
{
    (void)bounds;
    (void)radius;
    (void)segments;
    (void)width;
    (void)color;
    assert(0);
}
void RasterText(String value, int32_t x, int32_t y, int32_t font, Color color)
{
    (void)value;
    (void)x;
    (void)y;
    (void)font;
    (void)color;
    assert(0);
}
void RasterTextClipped(String value, int32_t x, int32_t y, int32_t font, Color color, Rectangle clip)
{
    (void)value;
    (void)x;
    (void)y;
    (void)font;
    (void)color;
    (void)clip;
    assert(0);
}
int32_t ImageWidth(String path)
{
    (void)path;
    return 0;
}
int32_t ImageHeight(String path)
{
    (void)path;
    return 0;
}
void RasterLine(Rectangle line, Color color)
{
    (void)line;
    (void)color;
    assert(0);
}
void RasterImage(String asset_path, uint32_t texture_id, Rectangle source,
                 Rectangle destination, Rectangle clip, Vector2 origin,
                 float rotation, float radius, Color tint)
{
    (void)asset_path;
    (void)texture_id;
    (void)source;
    (void)destination;
    (void)clip;
    (void)origin;
    (void)rotation;
    (void)radius;
    (void)tint;
    assert(0);
}
int32_t GetCharPressed(void)
{
    return 0;
}
bool IsKeyPressed(int32_t key)
{
    (void)key;
    return false;
}
bool IsKeyDown(int32_t key)
{
    (void)key;
    return false;
}
char *GetClipboardText(void)
{
    return "";
}
void SetClipboardText(char *text)
{
    (void)text;
    assert(0);
}
int32_t SystemClipboardOpenHost(void)
{
    return -1;
}
int32_t SystemClipboardByteHost(int32_t index)
{
    (void)index;
    return -1;
}
bool SystemClipboardWriteHost(String text)
{
    (void)text;
    assert(0);
    return false;
}
void *asset_entry_at(size_t index)
{
    (void)index;
    return NULL;
}
size_t asset_entry_total(void)
{
    return 0;
}
unsigned char *LoadFileData(char *path, int32_t *size)
{
    (void)path;
    *size = 0;
    return NULL;
}
void UnloadFileData(unsigned char *data)
{
    (void)data;
}
static TreeEntry focused(InnerBreeze *app, int32_t focus)
{
    for (int32_t index = 0; index < TreeCount(app->ui.session); ++index) {
        TreeEntry entry = TreeNodeAt(app->ui.session, index);
        if (entry.focus_id == focus) {
            return entry;
        }
    }
    assert(0);
    return (TreeEntry){0};
}
static bool has_focus(InnerBreeze *app, int32_t focus)
{
    for (int32_t index = 0; index < TreeCount(app->ui.session); ++index) {
        if (TreeNodeAt(app->ui.session, index).focus_id == focus) {
            return true;
        }
    }
    return false;
}
static ScrollResult render(InnerBreeze *app, int32_t offset, bool exhausted)
{
    PaintClear(app->ui.session);
    FrameTextReset(&app->ui.frame_text);
    if (exhausted) {
        app->ui.frame_text.used = (int32_t)sizeof(app->ui.frame_text.bytes) - 1;
    }
    TreeStart(app->ui.session, 1, (Rectangle){0, 0, app->ui.view_width, app->ui.view_height});
    BeginScrollFrame(app->ui.session, (Vector2){0, 0}, false, false, false, 0, 1.0);
    int32_t width = app->ui.view_width - AppScale(32);
    int32_t height = settings_telegram_settings_telegram_content_height(width) + AppScale(24);
    ScrollProps props = {0};
    props.key = 76000;
    props.bounds = (Rectangle){0, 0, app->ui.view_width, app->ui.view_height};
    props.content_height = height;
    props.scroll_offset = offset;
    props.scale = MetricsScale();
    ScrollResult scroll = Scroll(app->ui.session, props);
    assert(scroll.opened);
    int32_t y = (int32_t)scroll.content.y + AppScale(12);
    settings_telegram_settings_telegram_draw(app, AppScale(16), width, &y);
    assert(End(app->ui.session));
    assert(TreeFinish(app->ui.session));
    return scroll;
}
static bool hex_digit(unsigned char value)
{
    return (value >= '0' && value <= '9') || (value >= 'a' && value <= 'f');
}
static void assert_complete_review(InnerBreeze *app, const char *expected, bool *visible_digits,
                                   bool *visible_values)
{
    int32_t review_node = -1;
    TreeEntry review = {0};
    for (int32_t index = 0; index < TreeCount(app->ui.session); ++index) {
        TreeEntry entry = TreeNodeAt(app->ui.session, index);
        if (contains(entry.semantic_label, "Signing key fingerprint:")) {
            review_node = index;
            review = entry;
        }
    }
    assert(review_node >= 0);
    size_t digits = 0;
    for (int32_t index = 0; index < PendingPaintCount(app->ui.session); ++index) {
        PaintCommand paint = PendingPaintAt(app->ui.session, index);
        if (paint.node != review_node || paint.value.length == 0) {
            continue;
        }
        int32_t line_width = MeasureGlyphWidth(paint.value, paint.font, StringView("", 0));
        assert(paint.x >= review.clip.x);
        assert(paint.x + line_width <= review.clip.x + review.clip.width);
        assert(paint.x + line_width <= review.bounds.x + review.bounds.width);
        bool fully_visible = paint.y >= paint.clip.y &&
                             paint.y + paint.font <= paint.clip.y + paint.clip.height;
        if (fully_visible) {
            assert(paint.x >= paint.clip.x);
            assert(paint.x + line_width <= paint.clip.x + paint.clip.width);
        }
        size_t offset = 0;
        while (offset < paint.value.length) {
            size_t end = offset;
            while (end < paint.value.length && paint.value.data[end] != ' ') {
                ++end;
            }
            if (fully_visible) {
                String token = StringView(paint.value.data + offset, end - offset);
                for (size_t value = 0; value < ReviewValueCount; ++value) {
                    if (text_equal(token, review_values[value])) {
                        visible_values[value] = true;
                    }
                }
            }
            bool group = end - offset == 4;
            for (size_t byte = offset; byte < end; ++byte) {
                group = group && hex_digit((unsigned char)paint.value.data[byte]);
            }
            if (group) {
                for (size_t byte = offset; byte < end; ++byte) {
                    assert(digits < 256);
                    assert(paint.value.data[byte] == expected[digits]);
                    if (fully_visible) {
                        visible_digits[digits] = true;
                    }
                    ++digits;
                }
            }
            offset = end + 1;
        }
    }
    assert(digits == 256);
}
int main(void)
{
    InnerBreeze app = {0};
    app.ui.session = SessionOpen();
    lumi_telegram_linked = true;
    lumi_authorization_ready = true;
    lumi_authorization_state = 2;
    memcpy(lumi_authorization_pending.app_id, "inbe", 5);
    memset(lumi_authorization_pending.account_id, 'c', 64);
    memset(lumi_authorization_pending.node_id, 'b', 64);
    memset(lumi_authorization_pending.signing_key, 'a', 64);
    memset(lumi_authorization_pending.encryption_key, 'd', 2368);
    memset(lumi_authorization_pending.request_id, 'e', 32);
    memcpy(lumi_authorization_pending.audience, "https://api.waozi.xyz", 21);
    memcpy(lumi_authorization_pending.scopes[0].collection, "private.inbe.v2.lumi", 20);
    lumi_authorization_pending.scope_count = 1;
    lumi_authorization_pending.scopes[0].read = true;
    lumi_authorization_pending.scopes[0].write = true;
    lumi_authorization_pending.bot_id = 123456;
    lumi_authorization_pending.telegram_id = 700001;
    lumi_authorization_pending.expires_at = 1791529031;
    OwnerRendezvous original = lumi_authorization_pending;
    static const char expected[] =
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"
        "aa98ae86066a462dce12fdb1933b106077eabf1fb395dd3f8fabcc92b9ea16c2";
    static const struct {
        int32_t width;
        int32_t height;
        int32_t font;
        float scale;
    } layouts[] = {
        {320, 280, 16, 1.0f}, {400, 280, 24, 1.0f}, {900, 400, 24, 1.6f}
    };
    for (size_t layout = 0; layout < sizeof(layouts) / sizeof(layouts[0]); ++layout) {
        app.ui.view_width = layouts[layout].width;
        app.ui.view_height = layouts[layout].height;
        AppMetricsConfigure(layouts[layout].scale);
        AppMetricsConfigureFont(layouts[layout].font);
        ScrollResult scroll = render(&app, 0, false);
        assert(scroll.frame.scrollbar);
        assert(scroll.content.width < scroll.viewport.width);
        bool visible_digits[256] = {0};
        bool visible_values[ReviewValueCount] = {0};
        assert_complete_review(&app, expected, visible_digits, visible_values);
        int32_t maximum = scroll.max_scroll;
        for (int32_t offset = AppScale(16); offset < maximum; offset += AppScale(16)) {
            render(&app, offset, false);
            assert_complete_review(&app, expected, visible_digits, visible_values);
        }
        scroll = render(&app, 100000, false);
        assert_complete_review(&app, expected, visible_digits, visible_values);
        for (size_t digit = 0; digit < sizeof(visible_digits) / sizeof(visible_digits[0]); ++digit) {
            assert(visible_digits[digit]);
        }
        for (size_t value = 0; value < ReviewValueCount; ++value) {
            assert(visible_values[value]);
        }
        TreeEntry approve = focused(&app, 7652);
        assert(!approve.disabled);
        assert(approve.bounds.x + approve.bounds.width <= approve.clip.x + approve.clip.width);
        assert(memcmp(&original, &lumi_authorization_pending, sizeof(original)) == 0);
        render(&app, 100000, true);
        assert(focused(&app, 7652).disabled);
        truncated_review = true;
        render(&app, 100000, false);
        assert(focused(&app, 7652).disabled);
        truncated_review = false;
    }
    assert(lumi_authorization_intent == 0);

    /* A connected chat without a waiting Mini App request shows one action
       and a quiet disconnect, without Mini App controls. */
    lumi_authorization_ready = false;
    lumi_authorization_state = 0;
    memset(lumi_authorization_pending.request_id, 0, sizeof(lumi_authorization_pending.request_id));
    render(&app, 0, false);
    assert(has_focus(&app, 7650));
    assert(has_focus(&app, 7651));
    assert(!has_focus(&app, 7652));
    assert(!has_focus(&app, 7653));
    assert(!has_focus(&app, 7654));
    assert(SessionClose(app.ui.session));
    puts("Settings complete identifiers, fingerprints, active clipped paint and retained review checks passed");
    return 0;
}
