#include "platform/raylib_text_input.h"
#include "zir_string.h"

#include <assert.h>
#include <stdint.h>
#include <string.h>

static int32_t queued[8];
static int queued_at;
static bool control_down;
static bool paste_pressed;
static int32_t repeating_key;
static int32_t pressed_key;
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
    return (paste_pressed && key == TextInputKeyV) ||
        (pressed_key != 0 && key == pressed_key);
}

/* The OS repeats a held key; only that key's repeat is reported. */
bool
IsKeyPressedRepeat(int32_t key)
{
    return repeating_key != 0 && key == repeating_key;
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
    /* A held Backspace keeps deleting; a held paste shortcut acts once. */
    control_down = false;
    paste_pressed = false;
    queued[0] = 0;
    queued_at = 0;
    repeating_key = TextInputKeyBackspace;
    input = SampleTextFieldInput(true, typed_buffer);
    assert(input.backspace);
    assert(!input.delete_forward);
    control_down = true;
    repeating_key = TextInputKeyV;
    input = SampleTextFieldInput(true, typed_buffer);
    assert(!input.paste);
    repeating_key = 0;
    control_down = false;

    /* End moves to the line's end; Control+End to the text's end, and a
       text area must not see both. Home works the same way. */
    pressed_key = TextInputKeyEnd;
    TextAreaInput area = SampleTextAreaInput(true, typed_buffer);
    assert(area.end && !area.document_end);
    control_down = true;
    area = SampleTextAreaInput(true, typed_buffer);
    assert(area.document_end && !area.end);
    pressed_key = TextInputKeyHome;
    area = SampleTextAreaInput(true, typed_buffer);
    assert(area.document_home && !area.home);
    control_down = false;
    area = SampleTextAreaInput(true, typed_buffer);
    assert(area.home && !area.document_home);
    pressed_key = 0;
    assert(TextInputWriteClipboard(StringView("copied", 6)));
    assert(strcmp((const char *)clipboard, "copied") == 0);
    return 0;
}
