package xyz.waozi.inbe;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

/** One cancellable live stream. All MediaPlayer operations run on the main looper. */
final class RadioPlayer {
    interface Foreground { void active(boolean active); }
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AudioManager audio;
    private final Foreground foreground;
    private final AudioAttributes attributes = new AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build();
    private MediaPlayer player;
    private AudioFocusRequest focus;
    private boolean focused;
    private boolean interrupted;
    private volatile boolean wanted;
    private volatile int state;
    private String url;
    private float volume = 0.6f;
    private long retryDelay = 2000;
    private final Runnable reconnect = this::connect;
    private final Runnable timeout = this::retry;

    RadioPlayer(Context context, Foreground foreground) {
        audio = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        this.foreground = foreground;
    }

    int command(int action, String address, int percent) {
        if (action == 0) {
            // State queries stop immediately, even before the main looper runs.
            wanted = false;
            state = 0;
            handler.post(this::stop);
        } else if (action == 1) {
            if (address == null || !address.startsWith("https://")) return -1;
            wanted = true;
            state = 1;
            handler.post(() -> {
                wanted = true;
                start(address);
            });
        } else if (action == 2) {
            handler.post(() -> {
                volume = Math.max(0, Math.min(100, percent)) / 100f;
                applyVolume(false);
            });
        }
        return state;
    }

    private final AudioManager.OnAudioFocusChangeListener focusListener = change -> {
        if (change == AudioManager.AUDIOFOCUS_LOSS) {
            stop();
        } else if (change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) {
            interrupted = true;
            handler.removeCallbacks(reconnect);
            handler.removeCallbacks(timeout);
            releasePlayer();
            state = 0;
        } else if (change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK) {
            applyVolume(true);
        } else if (change == AudioManager.AUDIOFOCUS_GAIN) {
            if (interrupted && wanted) {
                interrupted = false;
                connect();
            }
            applyVolume(false);
        }
    };

    private void start(String address) {
        // A Stop queued after Play prevents its asynchronous preparation.
        if (!wanted) return;
        handler.removeCallbacks(reconnect);
        handler.removeCallbacks(timeout);
        releasePlayer();
        url = address;
        interrupted = false;
        retryDelay = 2000;
        if (!focused) {
            int result;
            if (Build.VERSION.SDK_INT >= 26) {
                focus = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                    .setAudioAttributes(attributes)
                    .setOnAudioFocusChangeListener(focusListener, handler).build();
                result = audio.requestAudioFocus(focus);
            } else {
                result = audio.requestAudioFocus(focusListener, AudioManager.STREAM_MUSIC,
                    AudioManager.AUDIOFOCUS_GAIN);
            }
            if (result != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) {
                wanted = false;
                state = -1;
                return;
            }
            focused = true;
        }
        foreground.active(true);
        connect();
    }

    private void connect() {
        if (!wanted || interrupted) return;
        releasePlayer();
        state = 1;
        MediaPlayer next = new MediaPlayer();
        player = next;
        next.setAudioAttributes(attributes);
        next.setVolume(volume, volume);
        next.setOnPreparedListener(prepared -> {
            if (player != prepared || !wanted || interrupted) return;
            handler.removeCallbacks(timeout);
            prepared.start();
            state = 2;
            retryDelay = 2000;
        });
        next.setOnErrorListener((failed, what, extra) -> {
            if (player == failed && wanted) retry();
            return true;
        });
        next.setOnCompletionListener(finished -> {
            if (player == finished && wanted) retry();
        });
        next.setOnInfoListener((current, what, extra) -> {
            if (current != player || !wanted) return false;
            if (what == MediaPlayer.MEDIA_INFO_BUFFERING_START) {
                state = 1;
                handler.removeCallbacks(timeout);
                handler.postDelayed(timeout, 20000);
            } else if (what == MediaPlayer.MEDIA_INFO_BUFFERING_END) {
                state = 2;
                handler.removeCallbacks(timeout);
            }
            return false;
        });
        try {
            next.setDataSource(url);
            next.prepareAsync();
            handler.postDelayed(timeout, 20000);
        } catch (Exception error) {
            retry();
        }
    }

    private void retry() {
        handler.removeCallbacks(timeout);
        handler.removeCallbacks(reconnect);
        releasePlayer();
        if (!wanted || interrupted) return;
        state = 3;
        handler.postDelayed(reconnect, retryDelay);
        retryDelay = Math.min(30000, retryDelay * 2);
    }

    private void applyVolume(boolean duck) {
        if (player != null) {
            float gain = duck ? volume * 0.2f : volume;
            player.setVolume(gain, gain);
        }
    }

    private void releasePlayer() {
        if (player == null) return;
        MediaPlayer old = player;
        player = null;
        old.setOnPreparedListener(null);
        old.setOnErrorListener(null);
        old.setOnCompletionListener(null);
        old.setOnInfoListener(null);
        old.release();
    }

    private void stop() {
        wanted = false;
        state = 0;
        handler.removeCallbacks(reconnect);
        handler.removeCallbacks(timeout);
        releasePlayer();
        if (focused) {
            if (Build.VERSION.SDK_INT >= 26 && focus != null) {
                audio.abandonAudioFocusRequest(focus);
            } else {
                audio.abandonAudioFocus(focusListener);
            }
            focused = false;
        }
        foreground.active(false);
    }
}
