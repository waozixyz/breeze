#include <stdint.h>
#include <string.h>
#include "session_mood.h"
#include "zir_string.h"

int32_t
data_discard_session(String path)
{
    return path.length == 4 && memcmp(path.data, "save", 4) == 0;
}

int32_t
data_save_session_checkin(uint8_t *path, SessionMoodCheckin *checkin)
{
    return strcmp((const char *)path, "save") == 0 &&
           checkin->mood_after == 4;
}

void profile_social_load_friends_cache(void *app) { (void)app; }
void profile_social_load_leaderboard_cache(void *app) { (void)app; }
void app_request_social_refresh(void *app) { (void)app; }
