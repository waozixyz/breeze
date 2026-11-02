#!/usr/bin/env python3
"""Test the production app adapter with OS/provider doubles, then real API compilation.

No phone, window, network, credentials or provider registration is used.
Kryon's own JNI tests cover transport persistence and envelope verification.
"""
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
KRYON = Path(os.environ.get("KRYON_DIR", ROOT / "build/packages/kryon"))
WORK = ROOT / "build/android-push-delivery-test"
JAVA = ROOT / "droid/app/src"

FIXTURES = {
    "android/Manifest.java": '''package android; public class Manifest {
        public static class permission { public static String POST_NOTIFICATIONS="post"; }}''',
    "android/os/Build.java": '''package android.os; public class Build {
        public static class VERSION { public static int SDK_INT=33; }}''',
    "android/content/SharedPreferences.java": '''package android.content;
        import java.util.*; public class SharedPreferences {
        final Map<String,Object> data=new HashMap<>(); public int commits;
        public String getString(String k,String d){return (String)data.getOrDefault(k,d);}
        public boolean getBoolean(String k,boolean d){return (Boolean)data.getOrDefault(k,d);}
        public Editor edit(){return new Editor();} public class Editor {
        public Editor putString(String k,String v){data.put(k,v);return this;}
        public Editor putBoolean(String k,boolean v){data.put(k,v);return this;}
        public boolean commit(){commits++;return true;} }}''',
    "android/content/Intent.java": "package android.content; public class Intent {}",
    "android/content/pm/PackageManager.java": '''package android.content.pm;
        public class PackageManager {public static int PERMISSION_GRANTED=0;
        public android.content.Intent getLaunchIntentForPackage(String p){return new android.content.Intent();}}''',
    "android/content/pm/ApplicationInfo.java": '''package android.content.pm;
        public class ApplicationInfo {public int icon=1;}''',
    "android/content/Context.java": '''package android.content;
        public class Context { public static int MODE_PRIVATE=0;
        public static String NOTIFICATION_SERVICE="notification";
        public static SharedPreferences prefs=new SharedPreferences();
        public static android.app.NotificationManager manager=new android.app.NotificationManager();
        public int permission;
        public SharedPreferences getSharedPreferences(String n,int m){return prefs;}
        public int checkSelfPermission(String p){return permission;}
        public Object getSystemService(String p){return manager;}
        public String getString(int id){return "Push notifications";}
        public String getPackageName(){return "test.breeze";}
        public android.content.pm.PackageManager getPackageManager(){return new android.content.pm.PackageManager();}
        public android.content.pm.ApplicationInfo getApplicationInfo(){return new android.content.pm.ApplicationInfo();}}''',
    "android/app/NotificationChannel.java": '''package android.app;
        public class NotificationChannel {public int importance;
        public NotificationChannel(String id,String name,int i){importance=i;}
        public int getImportance(){return importance;}}''',
    "android/app/NotificationManager.java": '''package android.app;
        public class NotificationManager {public static int IMPORTANCE_DEFAULT=3,IMPORTANCE_NONE=0;
        public boolean enabled=true,revoked; public int posts,cancels;
        public Notification last; public NotificationChannel channel;
        public boolean areNotificationsEnabled(){return enabled;}
        public void createNotificationChannel(NotificationChannel c){if(channel==null)channel=c;}
        public NotificationChannel getNotificationChannel(String id){return channel;}
        public void cancel(int id){cancels++;last=null;}
        public void notify(int id,Notification n){if(revoked)throw new SecurityException(); posts++;last=n;}}''',
    "android/app/PendingIntent.java": '''package android.app;
        public class PendingIntent {public static int FLAG_UPDATE_CURRENT=1,FLAG_IMMUTABLE=2;
        public static PendingIntent getActivity(android.content.Context c,int id,android.content.Intent i,int f){return new PendingIntent();}}''',
    "android/app/Notification.java": '''package android.app;
        public class Notification {public String title,body;
        public static class BigTextStyle {public BigTextStyle bigText(String b){return this;}}
        public static class Builder {Notification n=new Notification();
        public Builder(android.content.Context c){} public Builder(android.content.Context c,String id){}
        public Builder setSmallIcon(int i){return this;} public Builder setContentTitle(String t){n.title=t;return this;}
        public Builder setContentText(String b){n.body=b;return this;}
        public Builder setStyle(BigTextStyle s){return this;} public Builder setAutoCancel(boolean a){return this;}
        public Builder setContentIntent(PendingIntent p){return this;} public Notification build(){return n;}}}''',
    "org/json/JSONObject.java": '''package org.json; public class JSONObject {
        String value; public JSONObject(String s){if(s==null)throw new IllegalArgumentException();value=s;}
        public int optInt(String k){return Integer.parseInt(value);}
        public String optString(String k){return "wire";}}''',
    "org/kryonlabs/notifications/push/PushCallbacks.java": '''package org.kryonlabs.notifications.push;
        public class PushCallbacks {public static int starts,cancels;public static String scope="",wire="wire";
        public static boolean ready;public static int status=5;
        public static int start(android.content.Context c,String s,String label){starts++;scope=s;ready=true;return 5;}
        public static boolean cancel(android.content.Context c,String s){cancels++;ready=false;return true;}
        public static String snapshot(android.content.Context c,String s){return ready&&s.equals(scope)?Integer.toString(status):"1";}
        public static boolean accepts(android.content.Context c,int p,String w){return ready&&(status==4||status==5||status==7)&&(p==1||p==2)&&wire.equals(w);}}''',
    "org/kryonlabs/notifications/push/SharedPushService.java": '''package org.kryonlabs.notifications.push;
        public class SharedPushService extends android.content.Context {
        protected void onPushMessage(org.unifiedpush.android.connector.data.PushMessage m,String i){}}''',
    "org/kryonlabs/notifications/push/SharedFcmService.java": '''package org.kryonlabs.notifications.push;
        public class SharedFcmService extends android.content.Context {
        protected void onPushMessage(com.google.firebase.messaging.RemoteMessage m){}}''',
    "org/unifiedpush/android/connector/data/PushMessage.java": '''package org.unifiedpush.android.connector.data;
        public class PushMessage {byte[] content;public PushMessage(byte[] b){content=b;} public byte[] getContent(){return content;}}''',
    "com/google/firebase/messaging/RemoteMessage.java": '''package com.google.firebase.messaging;
        public class RemoteMessage {java.util.Map<String,String> data;
        public RemoteMessage(java.util.Map<String,String> d){data=d;} public java.util.Map<String,String> getData(){return data;}}''',
    "xyz/waozi/inbe/MainActivity.java": "package xyz.waozi.inbe; public class MainActivity extends android.content.Context {}",
    "xyz/waozi/inbe/BuildConfig.java": "package xyz.waozi.inbe; public class BuildConfig {public static boolean GPLAY=false;}",
    "xyz/waozi/inbe/R.java": '''package xyz.waozi.inbe; public class R {public static class string {
        public static int notification_channel_push=1,push_google_name=2;}}''',
    "xyz/waozi/inbe/PushDeliveryTest.java": r'''
package xyz.waozi.inbe;
import android.content.Context;
import org.kryonlabs.notifications.push.PushCallbacks;
public class PushDeliveryTest {
    static void require(boolean b,String label){if(!b)throw new AssertionError(label);}
    static void send(){PushNotificationDisplay.show(new Context(),1,"wire","Title","Body");}
    public static void main(String[] args) {
        MainActivity activity=new MainActivity();
        PushBridge.autoConnect(activity);
        require(PushCallbacks.starts==0,"no registration before native account/settings initialization");
        send(); require(Context.manager.posts==0,"no account");
        PushBridge.syncScope(activity,"account-one");
        require(PushCallbacks.starts==1,"enabled account starts shared registration");
        require(!PushBridge.isRegistered(activity),"endpoint must not claim server registration");
        PushBridge.syncScope(activity,"account-one");
        require(PushCallbacks.starts==1,"unchanged scope does not re-register");
        // New Context, with no Activity/session presence, models cold service delivery.
        send(); require(Context.manager.posts==1,"closed background display");
        int cancellations=Context.manager.cancels;
        Context denied=new Context();denied.permission=-1;
        PushNotificationDisplay.show(denied,1,"wire","Title","Body");
        require(Context.manager.posts==1,"Android permission denied");
        Context.manager.enabled=false;send();require(Context.manager.posts==1,"OS notifications disabled");
        Context.manager.enabled=true;Context.manager.channel.importance=0;
        send();require(Context.manager.posts==1,"channel disabled");Context.manager.channel.importance=3;
        PushNotificationDisplay.show(activity,1,"old-wire","Title","Body");
        PushNotificationDisplay.show(activity,3,"wire","Title","Body");
        PushNotificationDisplay.show(activity,1,"wire","Title","");
        PushNotificationDisplay.show(activity,1,"wire","x".repeat(257),"Body");
        PushNotificationDisplay.show(activity,1,"wire","Title","x".repeat(4097));
        require(Context.manager.posts==1,"invalid generation/provider/payload");
        PushBridge.disable(activity);send();require(Context.manager.posts==1,"explicit disable");
        require(Context.manager.last==null&&Context.manager.cancels==cancellations+1,"None removes visible body synchronously");
        PushBridge.syncScope(activity,"account-one");
        require(PushCallbacks.starts==1,"sync preserves explicit provider disable");
        PushBridge.configure(activity);send();require(Context.manager.posts==2,"explicit re-enable");
        PushBridge.syncScope(activity,"account-two");
        require(Context.manager.last==null&&Context.manager.cancels==cancellations+2,"replacement removes old visible body");
        require(PushCallbacks.cancels==2&&PushCallbacks.scope.equals("account-two"),"replace cancels former scope");
        PushBridge.syncScope(activity,"");send();
        require(Context.manager.posts==2&&!PushCallbacks.ready,"account revoke persists denial and cancels");
        require(Context.manager.last==null&&Context.manager.cancels==cancellations+3,"logout removes visible body");
        int commits=Context.prefs.commits;PushBridge.syncScope(activity,"");
        require(commits==Context.prefs.commits,"idle disabled ticks do not rewrite preferences");
        PushBridge.syncScope(activity,"account-three");
        Context.manager.revoked=true;send();Context.manager.revoked=false;
        require(Context.manager.posts==2,"permission revocation during dispatch handled");
        new PushServiceImpl().onPushMessage(new org.unifiedpush.android.connector.data.PushMessage(
                "Plain title\nReadable body".getBytes(java.nio.charset.StandardCharsets.UTF_8)),"wire");
        require(Context.manager.posts==3&&Context.manager.last.title.equals("Plain title"),"UP plain payload");
        java.util.Map<String,String> data=new java.util.HashMap<>();
        data.put("kryon_instance","wire");data.put("body","FCM body");
        new FcmPushService().onPushMessage(new com.google.firebase.messaging.RemoteMessage(data));
        require(Context.manager.posts==4&&Context.manager.last.title.equals("Inner Breeze"),"FCM data payload");
        PushCallbacks.status=4;send();require(Context.manager.posts==5,"registering current generation accepted");
        PushCallbacks.status=7;send();require(Context.manager.posts==6,"temporarily unavailable current generation accepted");
        PushCallbacks.status=6;send();require(Context.manager.posts==6,"failed generation rejected");
        PushCallbacks.status=1;send();require(Context.manager.posts==6,"disabled generation rejected");
        System.out.println("Breeze push account cancellation, disabled preferences, background display, permission/channel and payload tests passed");
    }
}
''',
}


def run(*args):
    subprocess.run([str(a) for a in args], check=True, timeout=60)


shutil.rmtree(WORK, ignore_errors=True)
source = WORK / "fixture"
for name, content in FIXTURES.items():
    target = source / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
production = [JAVA / f"{edition}/java/xyz/waozi/inbe/{name}.java" for edition, name in [
    ("main", "PushBridge"), ("main", "PushNotificationDisplay"),
    ("unified", "PushServiceImpl"), ("gplay", "FcmPushService"),
]]
run("javac", "-d", WORK / "classes", *source.rglob("*.java"), *production)
run("java", "-cp", WORK / "classes", "xyz.waozi.inbe.PushDeliveryTest")

# Compile the actual app and shared Java against installed APIs. This must
# succeed; missing libraries are a failure, never an unreported skip.
sdk = Path(os.environ.get("ANDROID_HOME", Path.home() / "Android/Sdk"))
jars = [sorted(sdk.glob("platforms/*/android.jar"))[-1]]
for group, artifact in [("org.unifiedpush.android", "connector"),
                        ("com.google.firebase", "firebase-messaging"),
                        ("com.google.android.gms", "play-services-tasks"),
                        ("com.google.android.gms", "play-services-basement")]:
    base = Path.home() / ".gradle/caches/modules-2/files-2.1" / group / artifact
    aar = sorted(base.glob("*/*/*.aar"))[-1]
    target = WORK / (artifact + ".jar")
    with ZipFile(aar) as archive:
        target.write_bytes(archive.read("classes.jar"))
    jars.append(target)
(source / "xyz/waozi/inbe/MainActivity.java").write_text(
    "package xyz.waozi.inbe; public class MainActivity extends android.app.Activity {}")
shared = sorted((KRYON / "templates/android-notifications-push").glob("*/java/**/*.java"))
stubs = [source / f"xyz/waozi/inbe/{name}.java" for name in ("MainActivity", "BuildConfig", "R")]
run("javac", "-cp", os.pathsep.join(map(str, jars)), "-d", WORK / "real-api",
    *stubs, *shared, *production,
    JAVA / "unified/java/xyz/waozi/inbe/UnifiedPushBridge.java",
    JAVA / "gplay/java/xyz/waozi/inbe/GplayPushBridge.java")
print("Breeze push adapters compile against actual Android, UnifiedPush and FCM APIs", flush=True)
