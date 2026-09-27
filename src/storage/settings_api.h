#ifndef INBE_STORAGE_SETTINGS_API_H
#define INBE_STORAGE_SETTINGS_API_H

int storage_settings_empty(void);
int storage_get_setting_int(const char *key, int fallback);
void storage_set_setting_int(const char *key, int value);
void storage_set_setting_text(const char *key, const char *value);
void storage_settings_begin_write(void);
void storage_settings_end_write(void);

#endif
