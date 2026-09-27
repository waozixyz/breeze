#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "app/language_selection.h"

static int32_t active_index;
static const char *system_preference = "es_AR.UTF-8";
static int font_loads;
static int refreshes;
static int saves;
static int seeds;
static int web_flushes;
static int web_platform;
static int setup_done;

static bool
equals(String value, const char *literal)
{
    size_t length = strlen(literal);
    return value.length == length &&
           memcmp(value.data, literal, length) == 0;
}

int32_t
LocaleLanguageCount(void)
{
    return 2;
}

LocaleLanguage
LocaleLanguageAt(int32_t index)
{
    LocaleLanguage language = {0};
    if (index == 0) {
        language.code = StringView("en", 2);
    } else if (index == 1) {
        language.code = StringView("es", 2);
    }
    return language;
}

bool
LocaleUse(String code)
{
    if (equals(code, "en")) {
        active_index = 0;
        return true;
    }
    if (equals(code, "es")) {
        active_index = 1;
        return true;
    }
    return false;
}

String
LocaleActiveCode(void)
{
    return LocaleLanguageAt(active_index).code;
}

int32_t
LocaleActiveIndex(void)
{
    return active_index;
}

String
LocaleSystemPreferences(void)
{
    return StringView(system_preference, strlen(system_preference));
}

String
LocalePreferred(String preferences)
{
    if (equals(preferences, "es_AR.UTF-8")) {
        return StringView("es", 2);
    }
    return StringView("missing", 7);
}

bool
LoadLocaleFont(InnerBreeze *app)
{
    assert(app != NULL);
    assert(app->language_index == active_index);
    assert(strcmp((char *)app->language,
                  active_index == 1 ? "es" : "en") == 0);
    font_loads++;
    return true;
}

void
refresh_locale_dependent_text(InnerBreeze *app)
{
    assert(app != NULL);
    assert(app->language_index == active_index);
    refreshes++;
}

void
save_settings(InnerBreeze *app)
{
    assert(app != NULL);
    saves++;
}

int32_t
settings_store_SettingsReadInt(String key, int32_t fallback)
{
    if (equals(key, "language_setup_done")) {
        return setup_done;
    }
    if (equals(key, "habits_screen_mode")) {
        return 99;
    }
    if (equals(key, "habits_tab")) {
        return -3;
    }
    if (equals(key, "habits_view_mode")) {
        return 99;
    }
    return fallback;
}

int32_t
WebPlatform(void)
{
    return web_platform;
}

int32_t
sync_web_storage_critical(void)
{
    web_flushes++;
    return 1;
}

int32_t
habits_seed_default_set_if_needed(Habits *habits)
{
    assert(habits != NULL);
    seeds++;
    habits->count = 1;
    return 1;
}

int
main(void)
{
    static InnerBreeze app;

    apply_language_selection(NULL, 1, 1);
    assert(font_loads == 0 && refreshes == 0 && saves == 0);

    apply_language_selection(&app, 1, 0);
    assert(app.language_system == 0 && app.language_selected == 1);
    assert(app.language_index == 1 && strcmp((char *)app.language, "es") == 0);
    assert(font_loads == 1 && refreshes == 1 && saves == 0);

    apply_language_selection(&app, -1, 1);
    assert(app.language_index == 0 && strcmp((char *)app.language, "en") == 0);
    assert(font_loads == 2 && refreshes == 2 && saves == 1);

    apply_system_language_selection(&app, 1);
    assert(app.language_system == 1 && app.language_index == 1);
    assert(strcmp((char *)app.language, "es") == 0);
    assert(font_loads == 3 && refreshes == 3 && saves == 2);

    system_preference = "unsupported";
    apply_system_language_selection(&app, 0);
    assert(app.language_system == 1 && app.language_index == 0);
    assert(strcmp((char *)app.language, "en") == 0);
    assert(font_loads == 4 && refreshes == 4 && saves == 2);

    app.language_system = 0;
    app.habits.selected = 5;
    app_accept_language_selection(&app);
    assert(saves == 3 && seeds == 1 && web_flushes == 0);
    assert(app.habits.screen_mode == HABITS_SCREEN_STATISTICS);
    assert(app.habits.tab == HABIT_TAB_WEEKLY);
    assert(app.habits.view_mode == HABIT_VIEW_WEEKLY);
    assert(app.habits.selected == -1);

    setup_done = 1;
    app_accept_language_selection(&app);
    assert(saves == 4 && seeds == 1);

    web_platform = 1;
    app.language_system = 1;
    system_preference = "es_AR.UTF-8";
    app_accept_language_selection(&app);
    assert(app.language_index == 1 && app.language_system == 1);
    assert(saves == 5 && seeds == 1 && web_flushes == 1);

    app_accept_language_selection(NULL);
    assert(saves == 5 && seeds == 1 && web_flushes == 1);
    return 0;
}
