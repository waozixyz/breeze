#include "ziran_host.h"
#include <stdio.h>
#include <string.h>

static int verify_children(const Bundle *bundle, int depth)
{
    int failures = 0;
    for (size_t index = 0; index < BundleAssetCount(bundle); index++) {
        const char *name = BundleAssetName(bundle, index);
        size_t length = strlen(name);
        if (length < 3 || strcmp(name + length - 3, ".zx") != 0) continue;
        fprintf(stderr, "bundled runtime: %s (%zu bytes)\n", name, BundleAssetSize(bundle, index));
        Bundle *child = BundleOpenBytes(BundleAssetData(bundle, index), BundleAssetSize(bundle, index));
        if (child == NULL) {
            fprintf(stderr, "bundled runtime rejected: %s\n", name);
            failures++;
            continue;
        }
        if (depth > 0) failures += verify_children(child, depth - 1);
        BundleClose(child);
    }
    return failures;
}

int main(int count, char **arguments)
{
    if (count != 2) return 2;
    Bundle *root = BundleOpen(arguments[1]);
    if (root == NULL) return 3;
    int failures = verify_children(root, 2);
    BundleClose(root);
    return failures == 0 ? 0 : 1;
}
