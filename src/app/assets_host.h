#ifndef INBE_ASSETS_HOST_H
#define INBE_ASSETS_HOST_H

#include <stddef.h>
#include <stdbool.h>
#include "assets.h"

typedef EmbeddedAssetEntry AssetEntry;
typedef AssetBlobResult AssetBlob;

extern const AssetEntry asset_entries[];
extern const size_t asset_entry_count;
const AssetEntry *asset_entry_at(size_t index);
size_t asset_entry_total(void);

#endif
