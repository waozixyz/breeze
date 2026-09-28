#include "platform/raylib_text_input.h"

#include <assert.h>
#include <stdint.h>
#include <string.h>

static int32_t queued[8];
static int queued_at;
static bool control_down;
static bool paste_pressed;
static uint8_t clipboard[32] = "pasted";


int32_t
GetCharPressed(void)
{
    int32_t value = queued[queued_at];
    if(value != 0)
        queued_at++;
    return value;
}

bool
IsKeyPressed(int32_t key)
{
    return paste_pressed && key == TextInputKeyV;
}

bool
IsKeyDown(int32_t key)
{
    return control_down && key == TextInputKeyLeftControl;
}

uint8_t *
GetClipboardText(void)
{
    return clipboard;
}

void
SetClipboardText(uint8_t *value)
{
    size_t length = strlen((const char *)value);
    assert(length < sizeof(clipboard));
    memcpy(clipboard, value, length + 1);
}

int
main(void)
{
    uint8_t bytes[16] = {0};
    Slice output = {bytes, sizeof(bytes)};
    int32_t used = 0;

    used = TextInputAppendCodepoint(output, used, 'A');
    used = TextInputAppendCodepoint(output, used, 0x00e9);
    used = TextInputAppendCodepoint(output, used, 0x20ac);
    used = TextInputAppendCodepoint(output, used, 0x1f600);
    assert(used == 10);
    assert(memcmp(bytes, "A\xc3\xa9\xe2\x82\xac\xf0\x9f\x98\x80", 11) == 0);

    assert(TextInputAppendCodepoint(output, used, 0x0a) == used);
    assert(TextInputAppendCodepoint(output, used, 0xd800) == used);
    assert(TextInputAppendCodepoint(output, used, 0x110000) == used);
    assert(TextInputAppendCodepoint(output, used, 'B') == 11);
    assert(bytes[11] == 0);

    uint8_t full[2] = {'a', 0};
    Slice short_output = {full, sizeof(full)};
    assert(TextInputAppendCodepoint(short_output, 1, 0x00e9) == 1);
    assert(full[0] == 'a' && full[1] == 0);

    uint8_t typed[16] = {0};
    Slice typed_buffer = {typed, sizeof(typed)};
    queued[0] = 0x00e9;
    queued[1] = 0;
    queued_at = 0;
    TextFieldInput input = SampleTextFieldInput(true, typed_buffer);
    assert(StringEqual(input.text, StringView("\xc3\xa9", 2)));
    assert(!input.paste);

    control_down = true;
    paste_pressed = true;
    queued[0] = 'v';
    queued[1] = 0;
    queued_at = 0;
    input = SampleTextFieldInput(true, typed_buffer);
    assert(input.text.length == 0);
    assert(input.paste);
    assert(StringEqual(input.paste_text, StringView("pasted", 6)));
    assert(TextInputWriteClipboard(StringView("copied", 6)));
    assert(strcmp((const char *)clipboard, "copied") == 0);
    return 0;
}
