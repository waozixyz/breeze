#include "android_package_assets_behavior.h"
#include "android_jni.h"
#include "assets_host.h"
#include <assert.h>
#include <string.h>

static NativeActivity activity;
static NativeAndroidApp app;
static int available;
static uint8_t package_bytes[] = {'Z', 'X', 0, 0, 26, 0, 0, 0};
static uint8_t apps_bytes[] = {'Z', 'X', 0, 0, 26, 0, 0, 0, 'A'};

typedef struct {
    int fail_open;
    int fail_buffer;
    int opens;
    int closes;
    int64_t length;
    uint8_t *bytes;
} TestAsset;

static TestAsset package_asset = {.bytes = package_bytes};
static TestAsset apps_asset = {.bytes = apps_bytes};

NativeAndroidApp *GetAndroidApp(void) { return available ? &app : NULL; }
size_t asset_entry_total(void) { return 0; }
const AssetEntry *asset_entry_at(size_t index) { (void)index; return NULL; }

void *AAssetManager_open(void *manager, uint8_t *path, int32_t mode)
{
    assert(manager == &activity);
    assert(mode == 3);
    TestAsset *asset;
    if (strcmp((char *)path, "inbe.zx") == 0) {
        asset = &package_asset;
    } else {
        assert(strcmp((char *)path, "apps.zx") == 0);
        asset = &apps_asset;
    }
    asset->opens++;
    return asset->fail_open ? NULL : asset;
}
int64_t AAsset_getLength64(void *handle)
{
    TestAsset *asset = handle;
    assert(asset == &package_asset || asset == &apps_asset);
    return asset->length;
}
uint8_t *AAsset_getBuffer(void *handle)
{
    TestAsset *asset = handle;
    assert(asset == &package_asset || asset == &apps_asset);
    return asset->fail_buffer ? NULL : asset->bytes;
}
void AAsset_close(void *handle)
{
    TestAsset *asset = handle;
    assert(asset == &package_asset || asset == &apps_asset);
    asset->closes++;
}

int main(void)
{
    assert(PackageSize() == 0);
    assert(AppsPackageSize() == 0);
    available = 1;
    assert(PackageSize() == 0);
    assert(AppsPackageSize() == 0);
    app.activity = &activity;
    assert(PackageSize() == 0 && package_asset.opens == 0);
    assert(AppsPackageSize() == 0 && apps_asset.opens == 0);
    activity.asset_manager = &activity;
    package_asset.fail_open = 1;
    assert(PackageSize() == 0 && package_asset.opens == 1 && package_asset.closes == 0);
    package_asset.fail_open = 0;
    assert(PackageSize() == 0 && package_asset.opens == 2 && package_asset.closes == 1);
    package_asset.length = sizeof(package_bytes);
    package_asset.fail_buffer = 1;
    assert(PackageSize() == 0 && package_asset.opens == 3 && package_asset.closes == 2);
    package_asset.fail_buffer = 0;
    assert(PackageSize() == sizeof(package_bytes) && package_asset.opens == 4 && package_asset.closes == 2);

    /* Loading one asset must not mark the other asset as loaded. */
    available = 0;
    app.activity = NULL;
    assert(PackageSize() == sizeof(package_bytes) && package_asset.opens == 4);
    assert(AppsPackageSize() == 0 && apps_asset.opens == 0);
    available = 1;
    app.activity = &activity;
    apps_asset.fail_open = 1;
    assert(AppsPackageSize() == 0 && apps_asset.opens == 1 && apps_asset.closes == 0);
    apps_asset.fail_open = 0;
    assert(AppsPackageSize() == 0 && apps_asset.opens == 2 && apps_asset.closes == 1);
    apps_asset.length = sizeof(apps_bytes);
    apps_asset.fail_buffer = 1;
    assert(AppsPackageSize() == 0 && apps_asset.opens == 3 && apps_asset.closes == 2);
    apps_asset.fail_buffer = 0;
    assert(AppsPackageSize() == sizeof(apps_bytes) && apps_asset.opens == 4 && apps_asset.closes == 2);
    assert(PackageSize() == sizeof(package_bytes) && package_asset.opens == 4);

    /* Both independent borrowed views survive Activity replacement. */
    NativeActivity replacement_activity = {0};
    app.activity = &replacement_activity;
    assert(PackageSize() == sizeof(package_bytes) && package_asset.opens == 4);
    assert(AppsPackageSize() == sizeof(apps_bytes) && apps_asset.opens == 4);
    available = 0;
    app.activity = NULL;
    assert(PackageSize() == sizeof(package_bytes) && package_asset.closes == 2);
    assert(AppsPackageSize() == sizeof(apps_bytes) && apps_asset.closes == 2);
    assert(MissingPackageAsset() && package_asset.opens == 4 && apps_asset.opens == 4);
    return 0;
}
