package xyz.waozi.inbe;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.util.Log;

/** Android's answer to an update installation. Confirmation goes to
 * Android's own installer screen; a finished or refused installation drops
 * the kept APK so it is not offered again. */
public final class AppUpdateReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirm = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirm != null) {
                confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                try {
                    context.startActivity(confirm);
                } catch (RuntimeException error) {
                    Log.w("InbeUpdate", "Android's installer is unavailable", error);
                }
            }
            return;
        }
        if (status == PackageInstaller.STATUS_SUCCESS) {
            AppUpdate.forget(context);
            return;
        }
        // A cancelled confirmation keeps the update for the next day's offer.
        if (status != PackageInstaller.STATUS_FAILURE_ABORTED) {
            Log.w("InbeUpdate", "Android did not install the update: " +
                    intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE));
            AppUpdate.forget(context);
        }
    }
}
