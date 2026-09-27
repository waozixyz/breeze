#ifndef APP_ANDROID_DEVICE_H
#define APP_ANDROID_DEVICE_H

#if ANDROID_BUILD
#include <jni.h>
#else
typedef void JNIEnv;
typedef void *jobject;
typedef int jint;
#endif

void android_device_init(void);
int android_device_system_dark(void);
int android_device_orientation(void);
void android_device_set_orientation_mode(int mode);
void android_device_set_soft_keyboard_visible(int visible);
int android_device_copy_text_and_toast(const char *text, const char *toast);
int android_device_app_icon(void);
int android_device_set_app_icon(int icon);
void android_device_native_set_system_dark(int dark);
void android_device_native_set_orientation(int orientation);
void android_device_native_text_input_commit(JNIEnv *env, jobject thiz, jint codepoint);
void android_device_native_text_input_backspace(JNIEnv *env, jobject thiz);
void android_device_native_text_input_enter(JNIEnv *env, jobject thiz);

#endif
