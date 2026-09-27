#ifndef INBE_ACTIVITY_JNI_H
#define INBE_ACTIVITY_JNI_H

#if defined(ANDROID_BUILD) && ANDROID_BUILD
#include <jni.h>

typedef struct ActivityJniSession {
    JavaVM *vm;
    JNIEnv *env;
    jobject activity;
    int attached;
} ActivityJniSession;

int activity_jni_attach(ActivityJniSession *session);
void activity_jni_detach(ActivityJniSession *session);

#endif

#endif
