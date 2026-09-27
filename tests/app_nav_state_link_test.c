#include "app/app_nav_state.h"

#include <assert.h>
#include <string.h>

static int account_present;
static const char *account_alias;

int32_t sync_account_load(SyncAccount *account)
{
    if (!account_present)
        return 0;
    memset(account, 0, sizeof(*account));
    memcpy(account->public_id, "abcdefghijklmnop", 16);
    return 1;
}

String storage_get_setting_text(String key)
{
    assert(StringEqual(key, StringView("sync_account_alias", 18)));
    return StringView(account_alias, strlen(account_alias));
}

String LocaleText(String key)
{
    assert(StringEqual(key, StringView("tab_profile", 11)));
    return StringView("Profile", 7);
}

String AppTextFromCString(uint8_t *data, int32_t capacity)
{
    int32_t length = 0;
    while (length < capacity && data[length] != 0)
        length++;
    return StringView((const char *)data, (size_t)length);
}

int main(void)
{
    InnerBreeze app;
    uint8_t name[64];
    uint8_t subtitle[64];
    uint8_t small[5];
    Slice out = {name, sizeof(name)};
    Slice sub = {subtitle, sizeof(subtitle)};
    memset(&app, 0, sizeof(app));

    app_reset_bottom_nav_routes(&app);
    assert(app.bottom_nav_route_count == 4);
    assert(app.bottom_nav_routes[0] == AppNavRoute_APP_NAV_ROUTE_ELIST);
    assert(app.bottom_nav_routes[1] == AppNavRoute_APP_NAV_ROUTE_HABITS);
    assert(app.bottom_nav_routes[2] == AppNavRoute_APP_NAV_ROUTE_PRACTICE);
    assert(app.bottom_nav_routes[3] == AppNavRoute_APP_NAV_ROUTE_SETTINGS);
    account_present = 0;
    account_alias = "";
    app_nav_profile_identity(&app, out, sizeof(name), sub, sizeof(subtitle));
    assert(strcmp((char *)name, "Profile") == 0);
    assert(subtitle[0] == 0);

    account_present = 1;
    account_alias = "nara";
    app_nav_profile_identity(&app, out, sizeof(name), sub, sizeof(subtitle));
    assert(strcmp((char *)name, "Nara") == 0);
    assert(strcmp((char *)subtitle, "@nara") == 0);

    memcpy(app.profile_display_name, "Breeze", 7);
    app_nav_profile_identity(&app, out, sizeof(name), sub, sizeof(subtitle));
    assert(strcmp((char *)name, "Breeze") == 0);
    assert(strcmp((char *)subtitle, "@nara") == 0);

    app.profile_display_name[0] = 0;
    account_alias = "";
    app_nav_profile_identity(&app, out, sizeof(name), sub, sizeof(subtitle));
    assert(strcmp((char *)name, "abcd...mnop") == 0);
    assert(strcmp((char *)subtitle, "Profile") == 0);

    app_nav_state_app_compact_public_id(StringView("abcdefghijklmnop", 16),
                                        (Slice){small, sizeof(small)}, 5);
    assert(strcmp((char *)small, "abcd") == 0);
    return 0;
}
