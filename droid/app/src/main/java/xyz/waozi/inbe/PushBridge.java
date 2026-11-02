package xyz.waozi.inbe;

import android.content.Context;
import android.content.SharedPreferences;
import java.lang.reflect.Method;
import org.json.JSONObject;
import org.kryonlabs.notifications.push.PushCallbacks;

final class PushBridge {
    private static final String PREFERENCES = "push";
    private static final String AUTO_CONNECT_DISABLED = "auto_connect_disabled";
    private static final String ACCOUNT_SCOPE = "account_scope";
    private static final String FEATURE_ENABLED = "feature_enabled";
    private static boolean nativeScopeKnown;

    private PushBridge() {}

    static boolean isRegistered(MainActivity activity) {
        // A provider endpoint alone is not a server registration. No push
        // server registration contract exists in Breeze yet.
        return false;
    }

    static synchronized void syncScope(Context context, String scope) {
        String next = scope == null ? "" : scope;
        if (next.length() > 128) next = "";
        android.content.SharedPreferences prefs = preferences(context);
        String previous = prefs.getString(ACCOUNT_SCOPE, "");
        boolean changed = !previous.equals(next);
        boolean first = !nativeScopeKnown;
        nativeScopeKnown = true;
        if (changed || (next.isEmpty() && (first || prefs.getBoolean(FEATURE_ENABLED, false)))) {
            // Persist denial before cancelling the former native generation.
            prefs.edit().putBoolean(FEATURE_ENABLED, false).commit();
            PushNotificationDisplay.cancel(context);
            if (!previous.isEmpty()) PushCallbacks.cancel(context, previous);
            prefs.edit().putString(ACCOUNT_SCOPE, next)
                    .putBoolean(FEATURE_ENABLED, !next.isEmpty()).commit();
        }
        if ((first || changed) && !next.isEmpty()) startCurrent(context);
    }

    private static void startCurrent(Context context) {
        android.content.SharedPreferences prefs = preferences(context);
        String scope = prefs.getString(ACCOUNT_SCOPE, "");
        if (!nativeScopeKnown || scope.isEmpty() ||
                !prefs.getBoolean(FEATURE_ENABLED, false) ||
                prefs.getBoolean(AUTO_CONNECT_DISABLED, false)) return;
        PushCallbacks.start(context, scope, "Inner Breeze");
    }

    static synchronized boolean canDisplay(Context context) {
        android.content.SharedPreferences prefs = preferences(context);
        String scope = prefs.getString(ACCOUNT_SCOPE, "");
        if (scope.isEmpty() || !prefs.getBoolean(FEATURE_ENABLED, false) ||
                prefs.getBoolean(AUTO_CONNECT_DISABLED, false)) return false;
        try {
            JSONObject state = new JSONObject(PushCallbacks.snapshot(context, scope));
            int status = state.optInt("status");
            return (status == 4 || status == 5 || status == 7) && !state.optString("wire").isEmpty();
        } catch (Exception invalidState) {
            return false;
        }
    }

    static String[] getDistributors(MainActivity activity) {
        Object value = callEdition("getDistributors", new Class<?>[] {MainActivity.class}, activity);
        return value instanceof String[] ? (String[]) value : new String[0];
    }

    static String[] getDistributorLabels(MainActivity activity) {
        Object value = callEdition("getDistributorLabels", new Class<?>[] {MainActivity.class}, activity);
        return value instanceof String[] ? (String[]) value : new String[0];
    }

    static String[] getDistributorIcons(MainActivity activity) {
        Object value = callEdition("getDistributorIcons", new Class<?>[] {MainActivity.class}, activity);
        return value instanceof String[] ? (String[]) value : new String[0];
    }

    static synchronized void configureWith(final MainActivity activity, final String pkg) {
        if (!BuildConfig.GPLAY) callEdition("configureWith",
                new Class<?>[] {MainActivity.class, String.class}, activity, pkg);
        configure(activity);
    }

    static synchronized void configure(final MainActivity activity) {
        preferences(activity).edit().putBoolean(AUTO_CONNECT_DISABLED, false).commit();
        startCurrent(activity);
    }

    static synchronized void autoConnect(final MainActivity activity) {
        // Native account/settings initialization must run before registration.
        startCurrent(activity);
    }

    // "None" in the picker: unregister and forget the distributor, so push
    // notifications stay off until one is chosen again.
    static synchronized void disable(final MainActivity activity) {
        preferences(activity).edit().putBoolean(AUTO_CONNECT_DISABLED, true).commit();
        PushNotificationDisplay.cancel(activity);
        String scope = preferences(activity).getString(ACCOUNT_SCOPE, "");
        if (!scope.isEmpty()) PushCallbacks.cancel(activity, scope);
    }

    private static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
    }

    private static Object callEdition(String name, Class<?>[] parameterTypes, Object... args) {
        try {
            Method method = Class.forName(BuildConfig.GPLAY ? "xyz.waozi.inbe.GplayPushBridge" : "xyz.waozi.inbe.UnifiedPushBridge").getDeclaredMethod(name, parameterTypes);
            method.setAccessible(true);
            Object value = method.invoke(null, args);
            return value != null ? value : Boolean.TRUE;
        } catch (ClassNotFoundException e) {
            return null;
        } catch (Exception e) {
            return null;
        }
    }
}
