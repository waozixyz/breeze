package xyz.waozi.inbe;

import android.content.Intent;
import java.io.File;

/** Explicit debug launches can offer one local bundle without installing it. */
public final class LocalNodeApp {
    public static final String EXTRA_LOCAL_NODE_APP = "local_node_app";

    /** A USB test can serve the explicitly offered bundle's children locally. */
    public static String origin(boolean debug, Intent intent) {
        if (!debug || intent == null || !intent.getBooleanExtra(EXTRA_LOCAL_NODE_APP, false)) {
            return null;
        }
        String value = intent.getStringExtra("local_package_origin");
        if (value == null || !value.startsWith("http://127.0.0.1:")) {
            return null;
        }
        String port = value.substring("http://127.0.0.1:".length());
        if (port.isEmpty() || port.length() > 5 || !port.matches("[0-9]+")) {
            return null;
        }
        int number = Integer.parseInt(port);
        return number > 0 && number <= 65535 ? value : null;
    }

    private LocalNodeApp() {
    }

    public static File offered(boolean debug, Intent intent, File folder) {
        if (!debug || intent == null || !intent.getBooleanExtra(EXTRA_LOCAL_NODE_APP, false)
                || folder == null) {
            return null;
        }
        File[] bundles = folder.listFiles(file -> file.isFile() && file.getName().endsWith(".zx"));
        if (bundles == null || bundles.length != 1) {
            return null;
        }
        return bundles[0];
    }
}
