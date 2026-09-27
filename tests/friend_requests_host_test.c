#include "friend_requests_behavior.h"
#include "friend_requests.h"

#include <stddef.h>
#include <string.h>

static const char *response = "{\"incoming\":[{},{}],\"outgoing\":[]}";

int32_t
storage_get_social_cache_json(String kind, uint8_t *out, int64_t out_size)
{
    size_t length = strlen(response);
    if(!StringEqual(kind, StringView("friends.requests", 16)) ||
       out_size < 0 || length >= (size_t)out_size)
        return 0;
    memcpy(out, response, length + 1);
    return 1;
}

String
app_text_from_cstring(uint8_t *text, int32_t capacity)
{
    size_t length = 0;
    while (length < (size_t)capacity && text[length] != 0)
        length++;
    return StringView((const char *)text, length);
}

int
main(void)
{
    if(Answer() != 42 || PendingRequestCountNow() != 2)
        return 1;
    response = "{\"incoming\":[],\"outgoing\":[]}";
    if(PendingRequestCountNow() != 0)
        return 2;
    return 0;
}
