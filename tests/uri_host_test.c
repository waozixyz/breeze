#include "platform/uri_host.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failures;

static void
check(int ok, const char *name)
{
    if(!ok) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    }
}

static int
read_file(const char *path, char *out, size_t cap)
{
    FILE *f = fopen(path, "rb");
    size_t n;

    if(f == NULL || cap == 0)
        return 0;
    n = fread(out, 1, cap - 1, f);
    fclose(f);
    out[n] = '\0';
    return 1;
}

int
main(void)
{
    char path[] = "/tmp/inbe-open-uri.XXXXXX";
    char got[256];
    int fd = mkstemp(path);

    check(!CanOpenURI(NULL), "CanOpenURI NULL");
    check(!CanOpenURI(""), "CanOpenURI empty");
    check(!OpenURI(NULL), "OpenURI NULL");
    check(!OpenURI(""), "OpenURI empty");

    check(fd >= 0, "capture temp file");
    if(fd >= 0)
        close(fd);
    setenv("INBE_TEST_OPEN_URI_CAPTURE", path, 1);

    check(OpenURI("monero:84abc?tx_amount=0.1"), "OpenURI custom scheme");
    check(read_file(path, got, sizeof(got)), "capture custom scheme");
    check(strcmp(got, "monero:84abc?tx_amount=0.1") == 0,
          "custom URI passed unchanged");

    check(OpenURI("bitcoin:bc1qexample?amount=0.01"), "OpenURI bitcoin");
    check(read_file(path, got, sizeof(got)), "capture bitcoin URI");
    check(strcmp(got, "bitcoin:bc1qexample?amount=0.01") == 0,
          "custom URI accepted without HTTP-only filtering");

    unlink(path);
    unsetenv("INBE_TEST_OPEN_URI_CAPTURE");

    return failures == 0 ? 0 : 1;
}
