package xyz.waozi.inbe;

import static org.junit.Assert.*;
import android.graphics.Rect;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityNodeProvider;
import java.nio.charset.StandardCharsets;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {28, 36}, manifest = Config.NONE)
public class AccessibilityViewTest {
    private static byte[] snapshot(String nodes) {
        return ("{\"width\":400,\"height\":800,\"nodes\":[" + nodes + "]}")
            .getBytes(StandardCharsets.UTF_8);
    }

    @Test public void controlsKeepIdentityAndExposeStateAndScaledBounds() {
        long[] request = new long[2];
        AccessibilityView view = new AccessibilityView(RuntimeEnvironment.getApplication(),
            (identity, action) -> { request[0] = identity; request[1] = action; return true; });
        view.layout(0, 0, 200, 400);
        view.update(snapshot("[81,13,0,20,40,120,100,5,\"Guide voice 🌿\"]"));
        AccessibilityNodeProvider provider = view.getAccessibilityNodeProvider();
        AccessibilityNodeInfo root = provider.createAccessibilityNodeInfo(-1);
        assertEquals(1, root.getChildCount());
        AccessibilityNodeInfo control = provider.createAccessibilityNodeInfo(1);
        assertEquals("Guide voice 🌿", control.getText().toString());
        assertTrue(control.isCheckable());
        assertTrue(control.isChecked());
        assertEquals("android.widget.Switch", control.getClassName());
        Rect bounds = new Rect();
        control.getBoundsInParent(bounds);
        assertEquals(new Rect(10, 20, 60, 50), bounds);
        assertTrue(provider.performAction(1, AccessibilityNodeInfo.ACTION_CLICK, null));
        assertArrayEquals(new long[] {81, 1}, request);
        view.update(snapshot("[81,13,0,20,40,120,100,1,\"Guide voice 🌿\"]"));
        assertFalse(provider.createAccessibilityNodeInfo(1).isChecked());
        assertTrue(provider.performAction(1, AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS, null));
        assertTrue(provider.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY).isAccessibilityFocused());
    }

    @Test public void staleDisabledAndPasswordNodesDoNotLeakOrAct() {
        AccessibilityView view = new AccessibilityView(RuntimeEnvironment.getApplication(),
            (identity, action) -> { fail("Disabled or removed control acted"); return false; });
        view.update(snapshot("[82,8,7,0,0,100,48,3,\"Download\"],"
            + "[83,9,12,0,60,100,108,24,\"secret\"]"));
        AccessibilityNodeProvider provider = view.getAccessibilityNodeProvider();
        assertFalse(provider.performAction(1, AccessibilityNodeInfo.ACTION_CLICK, null));
        AccessibilityNodeInfo passwordNode = provider.createAccessibilityNodeInfo(2);
        assertTrue(passwordNode.isPassword());
        assertEquals("", passwordNode.getText().toString());
        view.update("incomplete".getBytes(StandardCharsets.UTF_8));
        assertNotNull(provider.createAccessibilityNodeInfo(1));
        view.update(snapshot(""));
        assertNull(provider.createAccessibilityNodeInfo(1));
        assertFalse(provider.performAction(1, AccessibilityNodeInfo.ACTION_CLICK, null));
    }

    @Test public void scrollUsesTheNativeRetainedIdentity() {
        long[] request = new long[2];
        AccessibilityView view = new AccessibilityView(RuntimeEnvironment.getApplication(),
            (identity, action) -> { request[0] = identity; request[1] = action; return true; });
        view.update(snapshot("[84,55,0,0,0,400,800,0,\"\"]"));
        AccessibilityNodeProvider provider = view.getAccessibilityNodeProvider();
        assertTrue(provider.createAccessibilityNodeInfo(1).isScrollable());
        assertTrue(provider.performAction(1, AccessibilityNodeInfo.ACTION_SCROLL_FORWARD, null));
        assertArrayEquals(new long[] {84, 3}, request);
    }
}
