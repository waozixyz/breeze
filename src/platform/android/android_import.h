#ifndef ANDROID_IMPORT_H
#define ANDROID_IMPORT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    ANDROID_IMPORT_RESULT_NONE = 0,
    ANDROID_IMPORT_RESULT_SELECTED = 1,
    ANDROID_IMPORT_RESULT_CANCELLED = 2
};

enum {
    ANDROID_IMPORT_KIND_DATA = 0,
    ANDROID_IMPORT_KIND_SYNC_KEY = 1,
    ANDROID_IMPORT_KIND_AUDIO_SOUND = 2,
    ANDROID_IMPORT_KIND_AUDIO_MUSIC = 3
};

int32_t android_import_open_picker(uint8_t *mime_types);
int32_t android_import_open_picker_for(int32_t kind, uint8_t *mime_types);
int32_t android_import_poll_result(uint8_t *path, int32_t capacity);
int32_t android_import_poll_result_for(int32_t kind, uint8_t *path,
                                       int32_t capacity);

bool import_open_picker_host(int32_t kind, uint8_t *mime_types);
int32_t import_poll_result_host(int32_t kind, uint8_t *path,
                                int32_t capacity);

#if defined(ANDROID_BUILD) && ANDROID_BUILD
#include <jni.h>
void android_import_native_selected(JNIEnv *env, jobject thiz, jint kind, jstring path);
void android_import_native_cancelled(JNIEnv *env, jobject thiz, jint kind);
#endif

#endif
