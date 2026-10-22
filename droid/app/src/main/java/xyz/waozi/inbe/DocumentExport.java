package xyz.waozi.inbe;

import android.content.ContentResolver;
import android.content.Intent;
import android.net.Uri;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;

/** One system-picked document, staged privately until the native writer finishes. */
public final class DocumentExport {
    private File staged;
    private Uri destination;

    public static Intent picker(String filename, String mimeType) {
        if (filename == null || filename.isEmpty() || filename.length() > 240
                || filename.contains("/") || filename.contains("\\") || filename.contains("\0")) {
            throw new IllegalArgumentException("Invalid export filename");
        }
        return new Intent(Intent.ACTION_CREATE_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType(mimeType == null || mimeType.isEmpty() ? "application/octet-stream" : mimeType)
                .putExtra(Intent.EXTRA_TITLE, filename);
    }

    public synchronized String selected(File cache, Uri uri) throws IOException {
        clear();
        if (uri == null || !"content".equals(uri.getScheme())) {
            throw new IOException("No document selected");
        }
        staged = File.createTempFile("document-export-", ".tmp", cache);
        destination = uri;
        return staged.getAbsolutePath();
    }

    public synchronized boolean commit(ContentResolver resolver, String path) {
        if (staged == null || destination == null || !staged.getAbsolutePath().equals(path)) {
            return false;
        }
        try {
            if (!staged.isFile() || staged.length() == 0) {
                return false;
            }
            try (FileInputStream input = new FileInputStream(staged);
                 OutputStream output = resolver.openOutputStream(destination, "wt")) {
                if (output == null) {
                    return false;
                }
                byte[] buffer = new byte[8192];
                try {
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        output.write(buffer, 0, count);
                    }
                    output.flush();
                } finally {
                    java.util.Arrays.fill(buffer, (byte) 0);
                }
            }
            return true;
        } catch (IOException | SecurityException error) {
            return false;
        } finally {
            clear();
        }
    }

    public synchronized void clear() {
        if (staged != null) {
            staged.delete();
        }
        staged = null;
        destination = null;
    }
}
