#include "platform/uri.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    char path[] = "/tmp/inbe-uri-link.XXXXXX";
    char got[256];
    char oversized[4096];
    const char embedded_nul[] = {'a', 0, 'b'};
    const char *uri = "monero:84abc?tx_amount=0.1";
    FILE *capture;
    int fd = mkstemp(path);
    assert(fd >= 0);
    close(fd);
    assert(setenv("INBE_TEST_OPEN_URI_CAPTURE", path, 1) == 0);

    assert(CanOpenUri(StringView(uri, strlen(uri))));
    assert(OpenUri(StringView(uri, strlen(uri))));
    capture = fopen(path, "rb");
    assert(capture != NULL);
    size_t n = fread(got, 1, sizeof(got) - 1, capture);
    fclose(capture);
    got[n] = 0;
    assert(strcmp(got, uri) == 0);

    assert(!OpenUri(StringView("", 0)));
    assert(!OpenUri(StringView(embedded_nul, sizeof(embedded_nul))));
    memset(oversized, 'a', sizeof(oversized));
    assert(!OpenUri(StringView(oversized, sizeof(oversized))));

    unsetenv("INBE_TEST_OPEN_URI_CAPTURE");
    unlink(path);
    return 0;
}
