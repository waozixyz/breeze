package xyz.waozi.inbe;

import static org.junit.Assert.*;
import static org.robolectric.Shadows.shadowOf;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.os.Looper;
import java.lang.reflect.Field;
import java.time.Duration;
import java.util.ArrayList;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowMediaPlayer;
import org.robolectric.shadows.util.DataSource;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {23, 28, 36}, manifest = Config.NONE)
public class RadioPlayerTest {
    private static final String URL = "https://radio.stereoscenic.com/asp-s";
    private final ArrayList<Boolean> foreground = new ArrayList<>();
    private RadioPlayer radio;

    @Before public void setup() {
        ShadowMediaPlayer.addMediaInfo(DataSource.toDataSource(URL),
            new ShadowMediaPlayer.MediaInfo(3600000, 100));
        radio = new RadioPlayer(RuntimeEnvironment.getApplication(), foreground::add);
    }

    private MediaPlayer player() throws Exception {
        Field field = RadioPlayer.class.getDeclaredField("player");
        field.setAccessible(true);
        return (MediaPlayer) field.get(radio);
    }
    private void idle() { shadowOf(Looper.getMainLooper()).idle(); }
    private void advance(long milliseconds) {
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMillis(milliseconds));
    }
    private int state() { return radio.command(3, "", 0); }

    @Test public void startsOnlyOnPlayAndKeepsPlayingWithoutFrames() throws Exception {
        assertEquals(0, state());
        assertTrue(foreground.isEmpty());
        radio.command(1, URL, 60);
        idle();
        assertEquals(1, state());
        advance(100);
        assertEquals(2, state());
        assertTrue(player().isPlaying());
        assertEquals(Boolean.TRUE, foreground.get(0));
        radio.command(2, "", 25);
        idle();
        assertEquals(0.25f, shadowOf(player()).getLeftVolume(), 0.001f);
        advance(10000);
        assertEquals(2, state());
        radio.command(0, "", 0);
        idle();
        assertEquals(0, state());
        assertNull(player());
        assertEquals(Boolean.FALSE, foreground.get(foreground.size() - 1));
    }

    @Test public void reconnectsAndStopCancelsPreparationAndRetry() throws Exception {
        radio.command(1, URL, 60);
        idle();
        advance(100);
        MediaPlayer old = player();
        shadowOf(old).invokeErrorListener(1, 0);
        assertEquals(3, state());
        assertNull(player());
        advance(2000);
        assertNotSame(old, player());
        advance(100);
        assertEquals(2, state());
        shadowOf(player()).invokeErrorListener(1, 0);
        radio.command(0, "", 0);
        idle();
        advance(60000);
        assertEquals(0, state());
        assertNull(player());
        radio.command(1, URL, 60);
        idle();
        radio.command(0, "", 0);
        idle();
        advance(1000);
        assertEquals(0, state());
        assertNull(player());
    }

    @Test public void stopThenPlayAndFocusLossPreserveCommandOrder() throws Exception {
        radio.command(1, URL, 60);
        radio.command(0, "", 0);
        radio.command(1, URL, 60);
        idle();
        advance(100);
        assertEquals(2, state());
        Field field = RadioPlayer.class.getDeclaredField("focusListener");
        field.setAccessible(true);
        AudioManager.OnAudioFocusChangeListener focus =
            (AudioManager.OnAudioFocusChangeListener) field.get(radio);
        focus.onAudioFocusChange(AudioManager.AUDIOFOCUS_LOSS_TRANSIENT);
        assertEquals(0, state());
        assertNull(player());
        focus.onAudioFocusChange(AudioManager.AUDIOFOCUS_GAIN);
        advance(100);
        assertEquals(2, state());
        focus.onAudioFocusChange(AudioManager.AUDIOFOCUS_LOSS);
        advance(60000);
        assertEquals(0, state());
        assertNull(player());
    }
}
