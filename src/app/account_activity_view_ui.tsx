// Authored UI composition; native application state remains in account_activity_view.zi.
import * as NativeLayout from "kryon/layout";
import * as ActivityState from "account_activity";
import {
    ActivityCurrentTime,
    ActivityEndRemote,
    ActivityRemoteVisible,
    ActivityRequestPause
} from "account_activity";
import { ActivityFresh } from "account_activity_model";
import {
    ActivityIndicatorLabel,
    ActivityIndicatorVisible,
    ActivityOpenRemote,
    ActivityStatus,
    NewRound,
    NewStatusBuffer
} from "account_activity_view";
import { app_content_top_reserved } from "app_chrome";
import { InnerBreeze } from "app_types";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppFontSize, AppScale } from "metrics";
import { NativePresent } from "native_flags";
import { patterns_phase_label_key } from "patterns_rules";
import { practice_label } from "practice_registry";
import { session_window_practice } from "session_window_view";
import { TextUntilNul } from "std/text_buffer";
import { SunSalutationPoseName } from "sun_salutation_labels";
import { FormatNumberTemplate, FrameTextHold } from "text_buffers";
import { ScreenPatterns, ScreenSession, ScreenSunSalutation } from "types";

// The Practice page shows the running device’s acknowledged state.
export function ActivityDrawRemote(
    app: *InnerBreeze,
    hosted: boolean = false
): boolean {
    if (!NativePresent(app) || !ActivityRemoteVisible()) {
        return false;
    }
    let value = ActivityState.account_activity.remote;
    let session = app.ui.session;
    let left = AppScale(24n);
    let width = app.ui.view_width - left * 2n;
    let top = app_content_top_reserved(app) + AppScale(24n);
    let name = practice_label(session_window_practice(value.screen));
    <Text
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/activity/name"),
            bounds: {
                x: float32(left),
                y: float32(top),
                width: float32(width),
                height: float32(AppScale(56n))
            },
            text: name,
            size: AppScale(28n)
        }}
    />;
    let fresh = ActivityFresh(value, ActivityCurrentTime());
    let state_key = "activity_remote_running";
    if (!fresh) {
        state_key = "activity_remote_stale";
    } else if (value.paused !== 0n) {
        state_key = "activity_remote_paused";
    }
    <Text
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/activity/state"),
            bounds: {
                x: float32(left),
                y: float32(top + AppScale(72n)),
                width: float32(width),
                height: float32(AppScale(72n))
            },
            text: LocaleText(state_key),
            size: AppFontSize()
        }}
    />;
    let status_buffer = NewStatusBuffer();
    let status = ActivityStatus(value, status_buffer[:]);
    <Text
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/activity/progress"),
            bounds: {
                x: float32(left),
                y: float32(top + AppScale(148n)),
                width: float32(width),
                height: float32(AppScale(76n))
            },
            text: FrameTextHold(&app.ui.frame_text, status),
            size: AppScale(32n)
        }}
    />;
    let phase: string = "";
    if (value.screen === ScreenPatterns) {
        phase = LocaleText(patterns_phase_label_key(value.phase));
    } else if (value.screen === ScreenSunSalutation) {
        phase = SunSalutationPoseName(value.phase);
    } else if (value.screen === ScreenSession) {
        let round = NewRound();
        FormatNumberTemplate(
            LocaleText("session_round_label"),
            value.round,
            round[:]
        );
        phase = FrameTextHold(
            &app.ui.frame_text,
            TextUntilNul(round[:])
        );
    }
    if (phase.count > 0n) {
        <Text
            session={session}
            props={{
                key: NativeLayout.KeyHash("inbe/activity/phase"),
                bounds: {
                    x: float32(left),
                    y: float32(top + AppScale(232n)),
                    width: float32(width),
                    height: float32(AppScale(60n))
                },
                text: phase,
                size: AppFontSize()
            }}
        />;
    }
    let pending = ActivityState.account_activity.pending_control[0n] !== u8(0n);
    let label = "pause_button";
    if (pending) {
        label = "activity_control_pending";
    } else if (value.paused !== 0n) {
        label = "play_button";
    }
    if (!fresh) {
        if (
            (
                <Button
                    session={session}
                    props={{
                        key: NativeLayout.KeyHash("inbe/activity/end"),
                        bounds: {
                            x: float32(left),
                            y: float32(top + AppScale(308n)),
                            width: float32(width),
                            height: float32(AppScale(48n))
                        },
                        label: LocaleText("activity_end_session")
                    }}
                />
            )
        ) {
            ActivityEndRemote(app);
            ActivityState.account_activity.view_open = false;
        }
    } else if (
        (
            <Button
                session={session}
                props={{
                    key: NativeLayout.KeyHash("inbe/activity/pause"),
                    bounds: {
                        x: float32(left),
                        y: float32(top + AppScale(308n)),
                        width: float32(width),
                        height: float32(AppScale(48n))
                    },
                    label: LocaleText(label),
                    disabled: pending,
                    loading: pending
                }}
            />
        )
    ) {
        ActivityRequestPause(app, value.paused !== 0n ? 0n : 1n);
    }
    if (
        (
            <Button
                session={session}
                props={{
                    key: NativeLayout.KeyHash("inbe/activity/close"),
                    bounds: {
                        x: float32(left),
                        y: float32(top + AppScale(372n)),
                        width: float32(width),
                        height: float32(AppScale(44n))
                    },
                    label: hosted ? "Lumi" : LocaleText("close_button")
                }}
            />
        )
    ) {
        ActivityState.account_activity.view_open = false;
    }
    return true;
}

export function ActivityDrawIndicator(
    app: *InnerBreeze,
    hosted: boolean = false
): void {
    if (!ActivityIndicatorVisible(app, hosted)) {
        return;
    }
    let width = AppScale(240n);
    const available = app.ui.view_width - AppScale(16n);
    if (width > available) {
        width = available;
    }
    if (
        (
            <Button
                session={app.ui.session}
                props={{
                    key: NativeLayout.KeyHash("inbe/activity/open"),
                    bounds: {
                        x: float32(app.ui.view_width - width - AppScale(8n)),
                        y: float32(AppScale(72n)),
                        width: float32(width),
                        height: float32(AppScale(56n))
                    },
                    label: ActivityIndicatorLabel(app)
                }}
            />
        )
    ) {
        ActivityOpenRemote(app, hosted);
    }
}
