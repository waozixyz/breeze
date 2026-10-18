package xyz.waozi.inbe;

import android.content.Context;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.Build;
import android.view.MotionEvent;
import android.view.View;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityManager;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityNodeProvider;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Exposes the native widget tree to Android services without taking touch input. */
final class AccessibilityView extends View {
    interface Listener {
        boolean action(long identity, int action);
    }

    private static final int NONE = Integer.MIN_VALUE;
    private static final int DROPDOWN = 11;
    private static final int TOGGLE = 13;
    private static final int CHECKBOX = 14;
    private static final int SCROLL = 55;
    private static final int HEADING = 3;
    private static final int IMAGE = 6;
    private final Listener listener;
    private final AccessibilityManager manager;
    private final Provider provider = new Provider();
    private Map<Integer, Node> nodes = new HashMap<>();
    private Map<Long, Integer> identities = new HashMap<>();
    private List<Integer> order = new ArrayList<>();
    private int nextId = 1;
    private int focused = NONE;
    private int hovered = NONE;
    private int sourceWidth = 1;
    private int sourceHeight = 1;
    private String previous = "";

    private static final class Node {
        long identity;
        int kind;
        int role;
        int flags;
        String label;
        final Rect bounds = new Rect();

        boolean enabled() { return (flags & 2) == 0; }
        boolean editable() { return (flags & 16) != 0; }
        boolean interactive() { return (flags & 1) != 0; }
        boolean scrollable() { return kind == SCROLL; }
        boolean checkable() { return kind == TOGGLE || kind == CHECKBOX; }

        String className() {
            if (editable()) return "android.widget.EditText";
            if (kind == TOGGLE) return "android.widget.Switch";
            if (kind == CHECKBOX) return "android.widget.CheckBox";
            if (kind == DROPDOWN) return "android.widget.Spinner";
            if (scrollable()) return "android.widget.ScrollView";
            if (interactive()) return "android.widget.Button";
            if (role == IMAGE) return "android.widget.ImageView";
            return "android.widget.TextView";
        }
    }

    AccessibilityView(Context context, Listener listener) {
        super(context);
        this.listener = listener;
        manager = (AccessibilityManager) context.getSystemService(Context.ACCESSIBILITY_SERVICE);
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);
        setFocusable(false);
        setClickable(false);
    }

    boolean enabled() {
        return manager != null && manager.isEnabled();
    }

    void update(byte[] snapshot) {
        String value = new String(snapshot, StandardCharsets.UTF_8);
        if (value.equals(previous)) return;
        try {
            JSONObject document = new JSONObject(value);
            JSONArray rows = document.getJSONArray("nodes");
            int width = document.getInt("width");
            int height = document.getInt("height");
            if (width <= 0 || height <= 0) return;
            Map<Integer, Node> replacement = new HashMap<>();
            Map<Long, Integer> retained = new HashMap<>();
            List<Integer> replacementOrder = new ArrayList<>();
            for (int i = 0; i < rows.length(); i++) {
                JSONArray row = rows.getJSONArray(i);
                Node node = new Node();
                node.identity = row.getLong(0);
                node.kind = row.getInt(1);
                node.role = row.getInt(2);
                node.bounds.set(row.getInt(3), row.getInt(4), row.getInt(5), row.getInt(6));
                node.flags = row.getInt(7);
                node.label = (node.flags & 8) != 0 ? "" : row.getString(8);
                if (node.bounds.isEmpty() || retained.containsKey(node.identity)) continue;
                Integer id = identities.get(node.identity);
                if (id == null) id = nextId++;
                retained.put(node.identity, id);
                replacement.put(id, node);
                replacementOrder.add(id);
            }
            if (focused != NONE && !replacement.containsKey(focused)) {
                send(focused, AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUS_CLEARED);
                focused = NONE;
            }
            if (!replacement.containsKey(hovered)) hovered = NONE;
            nodes = replacement;
            identities = retained;
            order = replacementOrder;
            sourceWidth = width;
            sourceHeight = height;
            previous = value;
            send(AccessibilityNodeProvider.HOST_VIEW_ID, AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED);
        } catch (JSONException invalid) {
            // An incomplete snapshot never replaces the accepted tree.
        }
    }

    private Rect bounds(Node node) {
        float x = (float) getWidth() / sourceWidth;
        float y = (float) getHeight() / sourceHeight;
        return new Rect(Math.round(node.bounds.left * x), Math.round(node.bounds.top * y),
            Math.round(node.bounds.right * x), Math.round(node.bounds.bottom * y));
    }

    private void send(int id, int type) {
        if (!enabled() || getParent() == null) return;
        AccessibilityEvent event = AccessibilityEvent.obtain(type);
        event.setPackageName(getContext().getPackageName());
        event.setSource(this, id);
        Node node = nodes.get(id);
        if (node != null) {
            event.setClassName(node.className());
            if (!node.label.isEmpty()) event.getText().add(node.label);
        }
        getParent().requestSendAccessibilityEvent(this, event);
    }

    @Override public AccessibilityNodeProvider getAccessibilityNodeProvider() {
        return provider;
    }

    @Override public boolean dispatchHoverEvent(MotionEvent event) {
        if (!enabled() || !manager.isTouchExplorationEnabled()) return super.dispatchHoverEvent(event);
        int hit = NONE;
        if (event.getActionMasked() != MotionEvent.ACTION_HOVER_EXIT) {
            for (int i = order.size() - 1; i >= 0; i--) {
                int id = order.get(i);
                if (bounds(nodes.get(id)).contains((int) event.getX(), (int) event.getY())) {
                    hit = id;
                    break;
                }
            }
        }
        if (hit != hovered) {
            if (hit != NONE) send(hit, AccessibilityEvent.TYPE_VIEW_HOVER_ENTER);
            if (hovered != NONE) send(hovered, AccessibilityEvent.TYPE_VIEW_HOVER_EXIT);
            hovered = hit;
        }
        return hit != NONE;
    }

    private final class Provider extends AccessibilityNodeProvider {
        @Override public AccessibilityNodeInfo createAccessibilityNodeInfo(int id) {
            if (id == HOST_VIEW_ID) {
                AccessibilityNodeInfo root = AccessibilityNodeInfo.obtain(AccessibilityView.this);
                onInitializeAccessibilityNodeInfo(root);
                root.setClassName("android.view.ViewGroup");
                for (int child : order) root.addChild(AccessibilityView.this, child);
                return root;
            }
            Node node = nodes.get(id);
            if (node == null) return null;
            AccessibilityNodeInfo info = AccessibilityNodeInfo.obtain();
            info.setSource(AccessibilityView.this, id);
            info.setParent(AccessibilityView.this);
            info.setPackageName(getContext().getPackageName());
            info.setClassName(node.className());
            if (Build.VERSION.SDK_INT >= 28) info.setHeading(node.role == HEADING);
            info.setText(node.label);
            info.setEnabled(node.enabled());
            info.setVisibleToUser(isShown());
            info.setFocusable(true);
            info.setAccessibilityFocused(id == focused);
            info.setFocused((node.flags & 32) != 0);
            info.setPassword((node.flags & 8) != 0);
            info.setEditable(node.editable());
            info.setSelected((node.flags & 4) != 0);
            info.setCheckable(node.checkable());
            info.setChecked(node.checkable() && (node.flags & 4) != 0);
            info.setClickable(node.enabled() && node.interactive());
            info.addAction(id == focused ? AccessibilityNodeInfo.ACTION_CLEAR_ACCESSIBILITY_FOCUS
                : AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS);
            if (node.enabled() && node.interactive()) {
                info.addAction(AccessibilityNodeInfo.ACTION_CLICK);
                info.addAction(AccessibilityNodeInfo.ACTION_FOCUS);
            }
            if (node.scrollable()) {
                info.setScrollable(true);
                info.addAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD);
                info.addAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD);
            }
            Rect local = bounds(node);
            info.setBoundsInParent(local);
            int[] location = new int[2];
            getLocationOnScreen(location);
            local.offset(location[0], location[1]);
            info.setBoundsInScreen(local);
            return info;
        }

        @Override public AccessibilityNodeInfo findFocus(int focus) {
            if (focus == AccessibilityNodeInfo.FOCUS_ACCESSIBILITY) return createAccessibilityNodeInfo(focused);
            for (int id : order) {
                if ((nodes.get(id).flags & 32) != 0) return createAccessibilityNodeInfo(id);
            }
            return null;
        }

        @Override public boolean performAction(int id, int action, Bundle arguments) {
            Node node = nodes.get(id);
            if (node == null) return false;
            if (action == AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS) {
                if (focused == id) return false;
                if (focused != NONE) send(focused, AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUS_CLEARED);
                focused = id;
                send(id, AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUSED);
                return true;
            }
            if (action == AccessibilityNodeInfo.ACTION_CLEAR_ACCESSIBILITY_FOCUS) {
                if (focused != id) return false;
                focused = NONE;
                send(id, AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUS_CLEARED);
                return true;
            }
            if (!node.enabled()) return false;
            if (node.interactive() && action == AccessibilityNodeInfo.ACTION_CLICK) return listener.action(node.identity, 1);
            if (node.interactive() && action == AccessibilityNodeInfo.ACTION_FOCUS) return listener.action(node.identity, 2);
            if (node.scrollable() && action == AccessibilityNodeInfo.ACTION_SCROLL_FORWARD) return listener.action(node.identity, 3);
            if (node.scrollable() && action == AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD) return listener.action(node.identity, 4);
            return false;
        }
    }
}
