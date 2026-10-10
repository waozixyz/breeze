#include "storage/legacy_session_files.h"
#include "raylib.h"
#include <stddef.h>

/* Check the native boundary, rather than repeating the Ziran layout in a mock. */
_Static_assert(sizeof(LegacyPaths) == sizeof(FilePathList),
               "LegacyPaths must match raylib's FilePathList size");
_Static_assert(_Alignof(LegacyPaths) == _Alignof(FilePathList),
               "LegacyPaths must match raylib's FilePathList alignment");
_Static_assert(offsetof(LegacyPaths, count) == offsetof(FilePathList, count),
               "LegacyPaths must read raylib's real entry count");
_Static_assert(offsetof(LegacyPaths, paths) == offsetof(FilePathList, paths),
               "LegacyPaths must read raylib's real path pointer");
_Static_assert(sizeof(((LegacyPaths *)0)->count) == sizeof(((FilePathList *)0)->count),
               "LegacyPaths must match raylib's entry count width");
