#ifndef STORAGE_IMPORT_H
#define STORAGE_IMPORT_H

#include "storage.h"

int storage_export_zip(const char *path);
int storage_import_zip(const char *path);
int storage_import_zip_ex(const char *path, StorageImportMode mode);
int storage_inspect_import(const char *path, StorageImportInfo *info);

#endif
