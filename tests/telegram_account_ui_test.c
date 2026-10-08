#include "screens/telegram_account.h"
#include "session.h"
#include "tree.h"
#include "tree_input.h"
#include "paint_queue.h"
#include "text_buffers.h"
#include "metrics.h"
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static const char secret[] = "Recovery-phrase-sentinel";
static bool contains(String text, const char *needle)
{
    size_t length = strlen(needle);
    for (size_t i = 0; i + length <= text.length; ++i) {
        if (memcmp(text.data + i, needle, length) == 0) return true;
    }
    return false;
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
{ (void)bounds; (void)radius; (void)segments; (void)color; assert(0); }
void RasterRoundedRectangleOutline(Rectangle bounds, float radius, int32_t segments, float width, Color color)
{ (void)bounds; (void)radius; (void)segments; (void)width; (void)color; assert(0); }
void RasterText(String value, int32_t x, int32_t y, int32_t font, Color color)
{ (void)value; (void)x; (void)y; (void)font; (void)color; assert(0); }
void RasterTextClipped(String value, int32_t x, int32_t y, int32_t font, Color color, Rectangle clip)
{ (void)value; (void)x; (void)y; (void)font; (void)color; (void)clip; assert(0); }
int32_t ImageWidth(String path) { (void)path; return 0; }
int32_t ImageHeight(String path) { (void)path; return 0; }
void RasterLine(Rectangle line, Color color) { (void)line; (void)color; assert(0); }
void RasterImage(String asset_path, uint32_t texture_id, Rectangle source,
                 Rectangle destination, Rectangle clip, Vector2 origin,
                 float rotation, float radius, Color tint)
{
    (void)asset_path; (void)texture_id; (void)source; (void)destination;
    (void)clip; (void)origin; (void)rotation; (void)radius; (void)tint;
    assert(0);
}
int32_t GetCharPressed(void) { return 0; }
bool IsKeyPressed(int32_t key) { (void)key; return false; }
bool IsKeyDown(int32_t key) { (void)key; return false; }
char *GetClipboardText(void) { return ""; }
void SetClipboardText(char *text) { (void)text; assert(0); }
int32_t SystemClipboardOpenHost(void) { return -1; }
int32_t SystemClipboardByteHost(int32_t index) { (void)index; return -1; }
bool SystemClipboardWriteHost(String text) { (void)text; assert(0); return false; }
void *asset_entry_at(size_t index) { (void)index; return NULL; }
size_t asset_entry_total(void) { return 0; }
unsigned char *LoadFileData(char *path, int32_t *size) { (void)path; *size = 0; return NULL; }
void UnloadFileData(unsigned char *data) { (void)data; }

static int32_t render(InnerBreeze *app, TelegramAccountView *view)
{
    FrameTextReset(&app->ui.frame_text);
    TreeStart(app->ui.session, 1, (Rectangle){0, 0, app->ui.view_width, app->ui.view_height});
    int32_t action = telegram_account_DrawTelegramAccount(app, view);
    assert(TreeFinish(app->ui.session));
    for (int32_t i = 0; i < PendingPaintCount(app->ui.session); ++i) {
        PaintCommand paint = PendingPaintAt(app->ui.session, i);
        assert(!contains(paint.value, secret));
    }
    return action;
}
static TreeEntry node(Session session, int32_t focus)
{
    for (int32_t i = 0; i < TreeCount(session); ++i) {
        TreeEntry found = TreeNodeAt(session, i);
        if (found.focus_id == focus) return found;
    }
    assert(0);
    return (TreeEntry){0};
}
static void click(Session session, TreeEntry entry)
{
    float x = entry.bounds.x + entry.bounds.width / 2;
    float y = entry.bounds.y + entry.bounds.height / 2;
    TreePointerUpdate(session, (PointerFrame){x, y, true, true, false});
    TreePointerUpdate(session, (PointerFrame){x, y, false, false, true});
    TreePointerUpdate(session, (PointerFrame){x, y, false, false, false});
}
int main(void)
{
    TelegramAccountPassword password = {0};
    unsigned char mask[257] = {0};
    memcpy(password.value, "a\xc3\xa9\xe6\x97\xa5", 6);
    assert(telegram_account_TelegramAccountPasswordMask(&password, (Slice){mask, sizeof(mask)}));
    assert(strcmp((char *)mask, "***") == 0);
    password.value[0] = 0xff;
    assert(!telegram_account_TelegramAccountPasswordMask(&password, (Slice){mask, sizeof(mask)}));
    assert(mask[0] == 0);
    telegram_account_TelegramAccountClearPassword(&password);
    assert(password.value[0] == 0);
    memcpy(password.value, secret, sizeof(secret));
    InnerBreeze app = {0};
    app.ui.session = SessionOpen();
    app.ui.view_width = 400;
    app.ui.view_height = 360;
    AppMetricsConfigure(1.0f);
    TelegramAccountView view = {0};
    assert(telegram_account_DrawTelegramAccount(&app, &view) == 0);
    assert(!telegram_account_TelegramAccountActionAllowed(&view, 0));
    assert(!telegram_account_TelegramAccountActionAllowed(&view, 8));
    view.visible = true;
    view.review_complete = true;
    view.review_id = StringView("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 32);
    view.allowed_actions = (1u << 4) | (1u << 6);
    view.password = &password;
    view.password_label = StringView("Recovery passphrase", 19);
    static const char details[] =
        "Verified account identity\nAccount hash\nBot numeric identifier\nTelegram numeric user\n"
        "Issuing node identity\nIssuing audience\nDelegate installation\nLumi exact collection\n"
        "Read and write only\nPrivate key generation\nFinite grant expiry\nSigning public fingerprint\n"
        "Encryption public fingerprint\nCompare both fingerprints on your other device\n";
    view.details = StringView(details, sizeof(details) - 1);
    assert(render(&app, &view) == 0);
    assert(!view.review_seen);
    assert(node(app.ui.session, 76616).disabled);
    TreeEntry field = node(app.ui.session, 76602);
    assert(field.secure && field.has_text && field.text_bytes == strlen(secret));
    for (int32_t i = 0; i < TreeCount(app.ui.session); ++i) {
        TreeEntry found = TreeNodeAt(app.ui.session, i);
        if (found.focus_id == 76602) {
            unsigned char bytes[257];
            assert(TreeTextRange(app.ui.session, i, 0, (int32_t)strlen(secret),
                (Slice){bytes, sizeof(bytes)}).length == 0);
        }
    }
    view.scroll_offset = 100000;
    assert(render(&app, &view) == 0);
    assert(view.review_seen);
    assert(!node(app.ui.session, 76616).disabled);
    click(app.ui.session, node(app.ui.session, 76616));
    assert(render(&app, &view) == 6);
    view.review_id = StringView("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", 32);
    assert(render(&app, &view) == 0);
    assert(!view.review_seen && node(app.ui.session, 76616).disabled);
    view.scroll_offset = 100000;
    view.busy = true;
    assert(render(&app, &view) == 0);
    assert(node(app.ui.session, 76616).disabled);
    assert(!node(app.ui.session, 76614).disabled);
    click(app.ui.session, node(app.ui.session, 76614));
    assert(render(&app, &view) == 4);
    for (size_t i = 0; i < sizeof(password.value); ++i) assert(password.value[i] == 0);
    view.details = StringView(details + 1, sizeof(details) - 2);
    view.review_seen = true;
    view.review_complete = false;
    render(&app, &view);
    assert(!view.review_seen);
    assert(view.scroll_offset == 0);
    view.details = StringView("", 0);
    view.review_seen = true;
    view.busy = false;
    assert(!telegram_account_TelegramAccountApprovalReady(&view, true));
    view.details = StringView(details, sizeof(details) - 1);
    assert(!telegram_account_TelegramAccountApprovalReady(&view, false));
    view.review_complete = false;
    assert(!telegram_account_TelegramAccountApprovalReady(&view, true));
    assert(SessionClose(app.ui.session));
    puts("Telegram account retained UI, masked passphrase, consent and cancel checks passed");
    return 0;
}
