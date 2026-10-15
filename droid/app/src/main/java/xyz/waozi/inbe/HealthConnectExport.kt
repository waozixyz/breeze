package xyz.waozi.inbe

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import androidx.health.connect.client.feature.ExperimentalMindfulnessSessionApi
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.MindfulnessSessionRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.metadata.Metadata as HcMetadata
import java.io.File
import java.time.Instant
import kotlin.coroutines.Continuation
import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.startCoroutine

/**
 * One-way push of finished sessions into Health Connect: meditation
 * and the breathwork practices become mindfulness sessions (meditation /
 * breathing types), sun salutation becomes a yoga exercise session. The
 * native side writes the session list (start,end,activity per CSV line);
 * this object owns permissions, the incremental export marker and the
 * result toasts.
 */
@OptIn(ExperimentalMindfulnessSessionApi::class)
object HealthConnectExport {
    const val REQUEST_CODE = 1003

    private val PERMISSIONS = setOf(
        HealthPermission.getWritePermission(ExerciseSessionRecord::class),
        HealthPermission.getWritePermission(MindfulnessSessionRecord::class))

    private val contract = PermissionController.createRequestPermissionResultContract()

    /** Called from native settings via JNI; must run on the UI thread. */
    @JvmStatic
    fun start(activity: MainActivity, csvPath: String?) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O ||
            HealthConnectClient.getSdkStatus(activity) != HealthConnectClient.SDK_AVAILABLE) {
            toast(activity, activity.getString(R.string.health_connect_unavailable))
            return
        }
        activity.startActivityForResult(contract.createIntent(activity, PERMISSIONS), REQUEST_CODE)
        activity.lastHealthConnectPath = csvPath
    }

    @JvmStatic
    fun handleResult(activity: Activity, resultCode: Int, data: Intent?, csvPath: String?) {
        if (resultCode != Activity.RESULT_OK) {
            toast(activity, activity.getString(R.string.health_connect_cancelled))
            return
        }
        val granted = contract.parseResult(resultCode, data)
        if (!granted.containsAll(PERMISSIONS)) {
            toast(activity, activity.getString(R.string.health_connect_denied))
            return
        }
        if (csvPath == null) {
            toast(activity, activity.getString(R.string.health_connect_failed))
            return
        }
        Thread {
            try {
                val count = export(activity, csvPath)
                val message = activity.getString(
                    if (count > 0) R.string.health_connect_exported
                    else R.string.health_connect_nothing_new, count)
                toast(activity, message)
            } catch (e: SecurityException) {
                toast(activity, activity.getString(R.string.health_connect_denied))
            } catch (e: Exception) {
                toast(activity, activity.getString(R.string.health_connect_failed))
            }
        }.start()
    }

    private fun export(context: Context, csvPath: String): Int {
        val client = HealthConnectClient.getOrCreate(context)
        val prefs = context.getSharedPreferences("health_connect", Context.MODE_PRIVATE)
        val marker = prefs.getLong("last_export", 0L)
        val records = mutableListOf<Record>()
        var maxEnd = marker

        for (line in File(csvPath).readLines().drop(1)) {
            val parts = line.split(',')
            if (parts.size < 3) continue
            val start = parts[0].toLongOrNull() ?: continue
            val end = parts[1].toLongOrNull() ?: continue
            val activityId = parts[2].toIntOrNull() ?: continue
            if (end <= marker || end <= start) continue
            maxEnd = maxOf(maxEnd, end)
            val startTime = Instant.ofEpochSecond(start)
            val endTime = Instant.ofEpochSecond(end)
            if (activityId == 2) {
                records.add(
                    ExerciseSessionRecord(
                        startTime = startTime,
                        startZoneOffset = null,
                        endTime = endTime,
                        endZoneOffset = null,
                        metadata = HcMetadata.manualEntry(),
                        exerciseType = ExerciseSessionRecord.EXERCISE_TYPE_YOGA,
                        title = context.getString(R.string.health_connect_title_yoga)))
            } else if (activityId == 4) {
                // Health Connect has no Tai Chi type; it is a martial art.
                records.add(
                    ExerciseSessionRecord(
                        startTime = startTime,
                        startZoneOffset = null,
                        endTime = endTime,
                        endZoneOffset = null,
                        metadata = HcMetadata.manualEntry(),
                        exerciseType = ExerciseSessionRecord.EXERCISE_TYPE_MARTIAL_ARTS,
                        title = context.getString(R.string.health_connect_title_tai_chi)))
            } else {
                records.add(
                    MindfulnessSessionRecord(
                        startTime = startTime,
                        startZoneOffset = null,
                        endTime = endTime,
                        endZoneOffset = null,
                        metadata = HcMetadata.manualEntry(),
                        mindfulnessSessionType =
                            if (activityId == 1) MindfulnessSessionRecord.MINDFULNESS_SESSION_TYPE_MEDITATION
                            else MindfulnessSessionRecord.MINDFULNESS_SESSION_TYPE_BREATHING,
                        title =
                            if (activityId == 1) context.getString(R.string.health_connect_title_meditation)
                            else context.getString(R.string.health_connect_title_breathing)))
            }
        }
        if (records.isEmpty()) return 0

        runSuspend { client.insertRecords(records) }
        prefs.edit().putLong("last_export", maxEnd).apply()
        return records.size
    }

    /**
     * Runs a suspend call to completion on the current (background) thread
     * without pulling in kotlinx-coroutines: the stdlib startCoroutine
     * trampoline plus a latch.
     */
    private fun <T> runSuspend(block: suspend () -> T): T {
        val latch = java.util.concurrent.CountDownLatch(1)
        var outcome: Result<T>? = null
        block.startCoroutine(object : Continuation<T> {
            override val context: CoroutineContext
                get() = EmptyCoroutineContext
            override fun resumeWith(result: Result<T>) {
                outcome = result
                latch.countDown()
            }
        })
        latch.await()
        return outcome!!.getOrThrow()
    }

    private fun toast(context: Context, text: String) {
        Handler(Looper.getMainLooper()).post {
            Toast.makeText(context, text, Toast.LENGTH_LONG).show()
        }
    }
}
