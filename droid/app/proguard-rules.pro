# Native code finds MainActivity by its package name and registers private
# native methods by their Java names.
-keep class xyz.waozi.inbe.MainActivity { *; }

# Native code looks these up by class or method name through JNI/reflection.
-keep class xyz.waozi.inbe.ShareHelper { *; }
-keep class xyz.waozi.inbe.GplayPushBridge { *; }
-keep class org.kryonlabs.play.PlayBilling {
    public static java.lang.String call(android.app.Activity, java.lang.String);
}

# Manifest and platform callback entrypoints must keep their public shape.
-keep class xyz.waozi.inbe.FcmPushService { *; }
-keep class xyz.waozi.inbe.PushServiceImpl { *; }
-keep class xyz.waozi.inbe.SessionForegroundService { *; }
-keep class xyz.waozi.inbe.StartPracticeTile { *; }
-keep class xyz.waozi.inbe.StartPracticeWidget { *; }
