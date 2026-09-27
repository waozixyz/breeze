#include "settings_store.h"
#include "settings_cache.h"

#include <assert.h>
#include <string.h>

static int fail_load;

int
storage_list_settings(SettingVisitor callback, void *user)
{
    callback.call(callback.context, StringView("speed", 5),
                  StringView("3", 1), (int64_t)user);
    callback.call(callback.context, StringView("", 0),
                  StringView("ignored", 7), (int64_t)user);
    callback.call(callback.context, StringView("language", 8),
                  StringView("pt-BR", 5), (int64_t)user);
    callback.call(callback.context, StringView("optional", 8),
                  StringView("", 0), (int64_t)user);
    callback.call(callback.context, StringView("speed", 5),
                  StringView("9", 1), (int64_t)user);
    return !fail_load;
}

int
main(void)
{
    char language[16] = {0};

    assert(SettingsCacheLoad());
    assert(settings_cache_SettingsCacheInt(StringView("speed", 5), 1) == 3);
    assert(settings_cache_SettingsCacheCopyText(StringView("language", 8),
                                               (Slice){language,
                                                       sizeof(language)}));
    assert(strcmp(language, "pt-BR") == 0);
    assert(settings_cache_SettingsCacheInt(StringView("optional", 8), 7) == 7);
    fail_load = 1;
    assert(!SettingsCacheLoad());
    assert(!settings_cache_SettingsCacheContains(StringView("speed", 5)));
    settings_cache_SettingsCacheFree();
    return 0;
}
