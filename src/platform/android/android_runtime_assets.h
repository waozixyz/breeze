#ifndef APP_ANDROID_RUNTIME_ASSETS_H
#define APP_ANDROID_RUNTIME_ASSETS_H

#include <stdbool.h>
#include <stdint.h>

uint64_t android_asset_start_host(uint8_t *url, uint8_t *path,
                                  uint8_t *error, int32_t error_capacity);
bool android_asset_poll_host(uint64_t handle, int32_t *status,
                             int32_t *http_status, uint64_t *bytes,
                             uint64_t *total_bytes, uint8_t *error,
                             int32_t error_capacity);
void android_asset_release_host(uint64_t handle);

#if defined(ANDROID_BUILD) && ANDROID_BUILD
#include <jni.h>

void android_runtime_asset_native_succeeded(JNIEnv *env, jobject thiz,
                                            jlong handle, jlong bytes,
                                            jint http_status);
void android_runtime_asset_native_progress(JNIEnv *env, jobject thiz,
                                           jlong handle, jlong bytes,
                                           jlong total_bytes);
void android_runtime_asset_native_failed(JNIEnv *env, jobject thiz,
                                         jlong handle, jint http_status,
                                         jstring error);
#endif

#endif
