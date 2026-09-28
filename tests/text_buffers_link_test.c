#include "app/text_buffers.h"

#include <assert.h>
#include <stdint.h>
#include <string.h>

static void
expect(const char *format, int32_t value, const char *wanted)
{
    uint8_t buffer[64] = {0};
    Slice output = {buffer, sizeof(buffer)};
    assert(FormatNumberTemplate(StringView(format, strlen(format)), value,
                                output));
    assert(strcmp((const char *)buffer, wanted) == 0);
}

static void
expect_pair(const char *format, int32_t first, int32_t second,
            const char *wanted)
{
    uint8_t buffer[64] = {0};
    Slice output = {buffer, sizeof(buffer)};
    assert(FormatTwoNumberTemplate(StringView(format, strlen(format)),
                                   first, second, output));
    assert(strcmp((const char *)buffer, wanted) == 0);
}

int
main(void)
{
    uint8_t edited[12] = "walk";
    Slice edit_buffer = {edited, sizeof(edited)};
    uint8_t unterminated[3] = {'a', 'b', 'c'};
    Slice unterminated_buffer = {unterminated, sizeof(unterminated)};
    uint8_t short_buffer[4] = {1, 1, 1, 1};
    Slice short_output = {short_buffer, sizeof(short_buffer)};
    uint8_t formatted[96] = {0};
    Slice formatted_output = {formatted, sizeof(formatted)};
    FormatArg args[5] = {0};
    Slice arguments = {args, 5};
    FrameTextStore store = {0};
    char temporary[] = "ROUND 3";
    expect("ROUND %d", 12, "ROUND 12");
    expect("%d 라운드", 3, "3 라운드");
    expect("Round", 5, "Round");
    expect("100%% %d", 2, "100% 2");
    expect("%d", INT32_MIN, "-2147483648");
    expect_pair("Step %d of %d", 1, 3, "Step 1 of 3");
    expect_pair("第%d步，共%d步", 2, 5, "第2步，共5步");
    expect_pair("%d%% of %d", 50, 100, "50% of 100");
    assert(!FormatTwoNumberTemplate(StringView("%d", 2), 1, 2,
                                    short_output));
    assert(short_buffer[0] == 0);
    assert(!FormatNumberTemplate(StringView("%d", 2), 12345,
                                 short_output));
    assert(short_buffer[0] == 0);

    args[0].is_text = true;
    args[0].text = StringView("Pose", 4);
    args[1].number = 2;
    args[2].number = 5;
    args[3].number = 3;
    args[4].number = 7;
    const char *template = "%s, rep %d/%d, %d:%02d";
    assert(FormatTemplate(StringView(template, strlen(template)),
                          arguments, formatted_output));
    assert(strcmp((const char *)formatted, "Pose, rep 2/5, 3:07") == 0);
    assert(!FormatTemplate(StringView(template, strlen(template)),
                           arguments, short_output));
    assert(short_buffer[0] == 0);
    assert(!FormatTemplate(StringView("%q", 2),
                           (Slice){args, 1}, formatted_output));
    assert(formatted[0] == 0);
    assert(!FormatTemplate(StringView("%s", 2),
                           (Slice){args, 2}, formatted_output));
    assert(formatted[0] == 0);
    args[0].is_text = false;
    args[0].number = 26;
    args[1].number = 9;
    args[2].number = 3;
    assert(FormatTemplate(StringView("%04d-%02d-%02d", 14),
                          (Slice){args, 3}, formatted_output));
    assert(strcmp((const char *)formatted, "0026-09-03") == 0);
    args[0].number = -7;
    assert(FormatTemplate(StringView("%04d", 4),
                          (Slice){args, 1}, formatted_output));
    assert(strcmp((const char *)formatted, "-007") == 0);

    String held = FrameTextHold(&store, StringView(temporary,
                                                  strlen(temporary)));
    temporary[0] = 'X';
    assert(StringEqual(held, StringView("ROUND 3", 7)));
    assert(store.used == 8);
    assert(FrameTextHold(&store, StringView("next", 4)).length == 4);
    FrameTextReset(&store);
    assert(store.used == 0);
    store.used = FrameTextCapacity - 2;
    assert(FrameTextHold(&store, StringView("too long", 8)).length == 0);
    assert(store.used == FrameTextCapacity - 2);

    assert(AppReplaceText(edit_buffer, 4, 4, StringView("ing", 3)));
    assert(strcmp((const char *)edited, "walking") == 0);
    assert(AppReplaceText(edit_buffer, 0, 4, StringView("t", 1)));
    assert(strcmp((const char *)edited, "ting") == 0);
    assert(AppReplaceText(edit_buffer, 1, 4, StringView("", 0)));
    assert(strcmp((const char *)edited, "t") == 0);
    assert(AppReplaceText(edit_buffer, 1, 1, StringView("\xC3\xA9", 2)));
    assert(strcmp((const char *)edited, "t\xC3\xA9") == 0);
    assert(!AppReplaceText(edit_buffer, 0, 0,
                           StringView("too many bytes", 14)));
    assert(strcmp((const char *)edited, "t\xC3\xA9") == 0);
    assert(!AppReplaceText(edit_buffer, -1, 0, StringView("x", 1)));
    assert(!AppReplaceText(edit_buffer, 2, 1, StringView("x", 1)));
    assert(!AppReplaceText(unterminated_buffer, 0, 0,
                           StringView("x", 1)));
    assert(memcmp(unterminated, "abc", 3) == 0);
    return 0;
}
