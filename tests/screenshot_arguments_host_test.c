#include "screenshot_arguments.h"
#include "screenshot_request.h"
#include "screenshot_arguments_link.h"

#include <assert.h>
#include <string.h>

String
app_text_from_cstring(uint8_t *text, int32_t capacity)
{
    int32_t length = 0;
    while (length < capacity && text[length] != 0)
        length++;
    return StringView((const char *)text, (size_t)length);
}

void
ScreenshotArgumentsHostTest(void)
{
    uint8_t *argv[] = {
        (uint8_t *)"inbe", (uint8_t *)"--screenshot",
        (uint8_t *)"frame.png"
    };
    String values[3];
    Slice args = {values, 3};
    ScreenshotRequest request;

    assert(ScreenshotArguments(3, argv, args) == 3);
    request = ScreenshotParse(args, 640, 480, 13, true);
    assert(request.valid && request.active == 1);
    assert(strcmp((char *)request.output, "frame.png") == 0);
    assert(ScreenshotArguments(129, argv, args) == -1);
    assert(ScreenshotArguments(1, NULL, args) == -1);
    argv[1] = NULL;
    assert(ScreenshotArguments(3, argv, args) == -1);
    argv[1] = (uint8_t *)"--screenshot";
    assert(ScreenshotArguments(0, NULL, args) == 0);
    assert(ScreenshotArgumentCount(3, argv) == 3);
}
