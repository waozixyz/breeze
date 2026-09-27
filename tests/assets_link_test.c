#include "assets_link_behavior.h"
#include "assets_host.h"

#include <assert.h>
#include <string.h>

int
main(void)
{
    AssetBlob style = asset_lookup((uint8_t *)"assets/styles/inbe.kss");
    AssetBlob missing = asset_lookup((uint8_t *)"assets/styles/missing.kss");

    assert(style.found && style.size > 4);
    assert(memcmp(style.data, "Text", 4) == 0);
    assert(strcmp((const char *)style.mime, "text/plain") == 0);
    assert(!missing.found);
    assert(Answer() == 42);
    return 0;
}
