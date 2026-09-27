#ifndef ANDROID_SHARE_H
#define ANDROID_SHARE_H

#include <stddef.h>

/* Pass caller-owned bytes to the Android share sheet. */
int android_share_bytes(const unsigned char *data, size_t data_size, const char *filename,
                        const char *mime_type, const char *title);

#endif
