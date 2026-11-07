#define _POSIX_C_SOURCE 200809L
#include "style_apply_link_behavior.h"
#include "zir_string.h"

#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include "setting_visitor.h"
#include "style_customization.h"

static const char *style_keys[] = {
    "appearance.css.all", "appearance.css.lists", "appearance.css.habits",
    "appearance.css.practices", "appearance.css.diary", "appearance.css.lumi"
};
/* Where Breeze kept the sheets while they were KSS. */
static const char *legacy_keys[] = {
    "appearance.kss.all", "appearance.kss.lists", "appearance.kss.habits",
    "appearance.kss.practices", "appearance.kss.diary", "appearance.kss.lumi"
};
enum { ACCOUNTS = 4 };
static char account_styles[ACCOUNTS][6][8192];
static int account_present[ACCOUNTS][6];
static char legacy_styles[ACCOUNTS][6][8192];
static int legacy_present[ACCOUNTS][6];
static unsigned active_account;
static int style_writes;
#define saved_styles account_styles[active_account]

static void
put_style(unsigned account, int index, const char *text)
{
    strcpy(account_styles[account][index], text);
    account_present[account][index] = 1;
}

static void
put_legacy(unsigned account, int index, const char *text)
{
    strcpy(legacy_styles[account][index], text);
    legacy_present[account][index] = 1;
}

static int
key_is(String key, const char *name)
{
    return key.length == strlen(name) && memcmp(key.data, name, key.length) == 0;
}

void
__wrap_storage_set_setting_text(String key, String value)
{
    for(int index = 0; index < 6; index++) {
        if(key_is(key, style_keys[index])) {
            assert(value.length < sizeof(saved_styles[index]));
            memcpy(saved_styles[index], value.data, value.length);
            saved_styles[index][value.length] = 0;
            account_present[active_account][index] = 1;
            style_writes++;
            return;
        }
    }
    assert(0 && "unexpected style setting");
}

String
__wrap_storage_get_setting_text(String key)
{
    for(int index = 0; index < 6; index++) {
        if(key_is(key, style_keys[index])) {
            return StringView(saved_styles[index], strlen(saved_styles[index]));
        }
    }
    return StringView("", 0);
}

int32_t
__wrap_storage_list_settings(SettingVisitor callback, void *user)
{
    /* KSS settings come first, so a CSS setting read after one must win. */
    for(int index = 0; index < 6; index++) {
        if(legacy_present[active_account][index]) {
            const char *value = legacy_styles[active_account][index];
            callback.call(callback.context, StringView(legacy_keys[index], strlen(legacy_keys[index])),
                     StringView(value, strlen(value)), (int64_t)(intptr_t)user);
        }
    }
    for(int index = 0; index < 6; index++) {
        if(account_present[active_account][index]) {
            callback.call(callback.context, StringView(style_keys[index], strlen(style_keys[index])),
                     StringView(saved_styles[index], strlen(saved_styles[index])),
                     (int64_t)(intptr_t)user);
        }
    }
    return 1;
}

static void *
startup(void *argument)
{
    (void)argument;
    int result = StartupStyleCheck();
    if(result != 42) {
        fprintf(stderr, "Style startup check failed: %d: %s\n", result, style_error);
    }
    assert(result == 42);
    return NULL;
}

int
main(void)
{
    pthread_attr_t attributes;
    pthread_t thread;

    /* Android native threads have much smaller stacks than the host main
     * thread. Exercise the entire startup parser chain within that budget. */
    assert(pthread_attr_init(&attributes) == 0);
    assert(pthread_attr_setstacksize(&attributes, 1024 * 1024) == 0);
    assert(pthread_create(&thread, &attributes, startup, NULL) == 0);
    assert(pthread_join(thread, NULL) == 0);
    assert(pthread_attr_destroy(&attributes) == 0);
    assert(Answer() == 42);
    int custom = CustomizationCheck();
    if(custom != 42) {
        fprintf(stderr, "Custom appearance check failed: %d\n", custom);
    }
    assert(custom == 42);
    put_style(0, 0, "Button { border-radius: 24px; }");
    put_style(0, 5, "Button { border-radius: 7px; }");
    assert(AccountStylesCheck(StringView(saved_styles[0], strlen(saved_styles[0])),
                             StringView(saved_styles[5], strlen(saved_styles[5]))) == 42);
    active_account = 1;
    assert(AccountStylesCheck(StringView("", 0), StringView("", 0)) == 42);
    active_account = 0;
    assert(AccountStylesCheck(StringView(saved_styles[0], strlen(saved_styles[0])),
                             StringView(saved_styles[5], strlen(saved_styles[5]))) == 42);

    /* Sheets saved as KSS convert to CSS once and are saved as CSS; one
     * without a CSS form opens as a draft and nothing is saved for it. */
    static const char *failing = "Button { gap: 1; }\n@variant big \"Big\" { Button { gap: 2; } }\n";
    active_account = 2;
    put_legacy(2, 0, "Button { radius: 24; }\n");
    put_legacy(2, 1, failing);
    style_writes = 0;
    int legacy = LegacyStylesCheck(StringView(failing, strlen(failing)));
    if(legacy != 42) {
        fprintf(stderr, "KSS settings check failed: %d: %s\n", legacy, style_error);
    }
    assert(legacy == 42);
    assert(style_writes == 1 && account_present[2][0] && !account_present[2][1]);
    assert(strstr(account_styles[2][0], "border-radius: 24px") != NULL);
    assert(strstr(legacy_styles[2][0], "radius: 24;") != NULL);
    /* The next start reads the CSS setting and converts nothing again. */
    style_writes = 0;
    assert(LegacyStylesCheck(StringView(failing, strlen(failing))) == 42);
    assert(style_writes == 0);

    /* A CSS setting wins over the KSS one whatever their order. */
    active_account = 3;
    put_legacy(3, 0, "Button { radius: 7; }\n");
    put_style(3, 0, "Button { border-radius: 24px; }");
    style_writes = 0;
    assert(AccountStylesCheck(StringView(saved_styles[0], strlen(saved_styles[0])),
                             StringView("", 0)) == 42);
    assert(style_writes == 0);
    return 0;
}
