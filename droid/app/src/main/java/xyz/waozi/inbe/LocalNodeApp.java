package xyz.waozi.inbe;

import android.content.Intent;
import java.io.File;

/** Explicit debug launches can offer one local bundle without installing it. */
public final class LocalNodeApp {
    public static final String EXTRA_LOCAL_NODE_APP = "local_node_app";

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
