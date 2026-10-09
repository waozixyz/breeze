#define _POSIX_C_SOURCE 200809L
#include "style_apply_link_behavior.h"

#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include "setting_visitor.h"
#include "style_customization.h"

static const char *style_keys[] = {
    "appearance.kss.all", "appearance.kss.lists", "appearance.kss.habits",
    "appearance.kss.practices", "appearance.kss.diary", "appearance.kss.lumi"
};
static char account_styles[2][6][8192];
static unsigned active_account;
#define saved_styles account_styles[active_account]

void
__wrap_storage_set_setting_text(String key, String value)
{
    for(int index = 0; index < 6; index++) {
        if(key.length == strlen(style_keys[index]) &&
           memcmp(key.data, style_keys[index], key.length) == 0) {
            assert(value.length < sizeof(saved_styles[index]));
            memcpy(saved_styles[index], value.data, value.length);
            saved_styles[index][value.length] = 0;
            return;
        }
    }
    assert(0 && "unexpected style setting");
}

String
__wrap_storage_get_setting_text(String key)
{
    for(int index = 0; index < 6; index++) {
        if(key.length == strlen(style_keys[index]) &&
           memcmp(key.data, style_keys[index], key.length) == 0) {
            return StringView(saved_styles[index], strlen(saved_styles[index]));
        }
    }
    return StringView("", 0);
}

int32_t
__wrap_storage_list_settings(SettingVisitor callback, void *user)
{
    for(int index = 0; index < 6; index++) {
        callback.call(callback.context, StringView(style_keys[index], strlen(style_keys[index])),
                 StringView(saved_styles[index], strlen(saved_styles[index])),
                 (int64_t)(intptr_t)user);
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
    strcpy(account_styles[0][0], "Button { radius: 24; }");
    strcpy(account_styles[0][5], "Button { radius: 7; }");
    assert(AccountStylesCheck(StringView(saved_styles[0], strlen(saved_styles[0])),
                             StringView(saved_styles[5], strlen(saved_styles[5]))) == 42);
    active_account = 1;
    assert(AccountStylesCheck(StringView("", 0), StringView("", 0)) == 42);
    active_account = 0;
    assert(AccountStylesCheck(StringView(saved_styles[0], strlen(saved_styles[0])),
                             StringView(saved_styles[5], strlen(saved_styles[5]))) == 42);
    return 0;
}
