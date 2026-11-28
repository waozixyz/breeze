import { Scroll } from "kryon/tsx/scroll";
import * as Layout from "kryon/layout";
import * as NativeField from "kryon/text_field";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import * as Sortable from "kryon/sortable";
import { Rectangle } from "kryon/geometry";
import { StyleTokenColor } from "kryon/drawing_props";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { SortableIndicator, SortableItem } from "kryon/tsx/sortable";
import { Spinbox } from "kryon/tsx/spinbox";
import { Text } from "kryon/tsx/text";
import { TextField } from "kryon/tsx/text_field";
import { InnerBreeze } from "app_types";
import { MutedTextClass } from "cards";
import { HostSeconds } from "host_clock";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, AppSmallFontSize } from "metrics";
import { FormatArg } from "text_buffers";
import { PackageFree, PackageText } from "package_files";
import {
    workout_builder,
    WORKOUT_BUILDER_EDITOR,
    WORKOUT_BUILDER_LIBRARY,
    WORKOUT_BUILDER_NAME_FIELD,
    WORKOUT_BUILDER_PICKER,
    WORKOUT_BUILDER_PLAY,
    WORKOUT_BUILDER_ROW_BLOCK,
    WORKOUT_BUILDER_ROW_END,
    WORKOUT_BUILDER_ROW_GROUP,
    WORKOUT_BUILDER_STAY,
    WorkoutBuilderAcceptInsertion,
    WorkoutBuilderBack,
    WorkoutBuilderButtonProps,
    WorkoutBuilderCanGroup,
    WorkoutBuilderCanPlay,
    WorkoutBuilderChanged,
    WorkoutBuilderClock,
    WorkoutBuilderControl,
    WorkoutBuilderDetail,
    WorkoutBuilderDrop,
    WorkoutBuilderDropped,
    WorkoutBuilderEdit,
    WorkoutBuilderExercise,
    WorkoutBuilderFits,
    WorkoutBuilderFormat,
    WorkoutBuilderFreeSlot,
    WorkoutBuilderGroupChosen,
    WorkoutBuilderGroupDetail,
    WorkoutBuilderGroupTitle,
    WorkoutBuilderTitleBuffer,
    WorkoutBuilderTextBuffer,
    WorkoutBuilderHeaderHeight,
    WorkoutBuilderIndent,
    WorkoutBuilderInsertionAt,
    WorkoutBuilderNameBuffer,
    WorkoutBuilderPictureCopies,
    WorkoutBuilderRow,
    WorkoutBuilderSave,
    WorkoutBuilderScrollOffset,
    WorkoutBuilderScrollProps,
    WorkoutBuilderShift,
    WorkoutBuilderSlice,
    WorkoutBuilderStartChoosing,
    WorkoutBuilderStatus,
    WorkoutBuilderStopChoosing,
    WorkoutBuilderStride,
    WorkoutBuilderTap,
    WorkoutBuilderThumbnail,
    WorkoutBuilderTile,
    WorkoutBuilderTouch,
    WorkoutBuilderTryInsert,
    WorkoutBuilderTryInsertRoutine,
    WorkoutBuilderVariantCount,
    WorkoutBuilderVariantKey
} from "workout_builder";
import {
    WORKOUT_NODE_GROUP,
    WORKOUT_PLAN_NODE_LIMIT,
    WORKOUT_PLAN_REPEAT_MAX,
    WorkoutNode,
    WorkoutPlan,
    WorkoutPlanAdjustRepeats,
    WorkoutPlanAdjustRest,
    WorkoutPlanAdjustSeconds,
    WorkoutPlanDuplicate,
    WorkoutPlanEnd,
    WorkoutPlanExercise,
    WorkoutPlanName,
    WorkoutPlanRemove,
    WorkoutPlanSetVariant,
    WorkoutPlanTimesOf,
    WorkoutPlanUngroup
} from "workout_plan";
import { WORKOUT_MOVE_COUNT } from "workout_rules";
import {
    WORKOUT_CUSTOM_MAX_SECONDS,
    WORKOUT_CUSTOM_MIN_SECONDS,
    WORKOUT_CUSTOM_REST_MAX,
    WORKOUT_CUSTOM_ROUTINE_LIMIT,
    WorkoutBlockSupports
} from "workout_sequence";

function WorkoutBuilderField(
    app: NativeRef<InnerBreeze>,
    state: NativeRef<NativeField.State>,
    field: s32,
    bounds: Rectangle,
    key: string
): boolean {
    const result = TextField({
        session: app.ui.session,
        state: state,
        props: {
            key: Layout.KeyHash(key),
            id: field,
            focus_id: field,
            bounds: bounds,
            label: LocaleText(key),
            placeholder: LocaleText(key)
        }
    });
    if (result.committed || result.escaped) {
        state.focused = false;
    }
    return result.changed;
}

function WorkoutBuilderCard(
    app: NativeRef<InnerBreeze>,
    key: u64,
    bounds: Rectangle,
    selected: boolean,
    fill: string
): void {
    let border = StyleTokenColor(selected ? "accent" : "text");
    if (!selected) {
        border.a = u8(46n);
    }
    <Box
        session={app.ui.session}
        props={{
            key: key,
            bounds: bounds,
            fill: StyleTokenColor(fill),
            border: border,
            radius: float32(AppScale(12n))
        }}
    />;
}

function WorkoutBuilderLabels(
    app: NativeRef<InnerBreeze>,
    bounds: Rectangle,
    title: string,
    detail: string
): void {
    let half = bounds.height / 2.0;
    let strong: [NativeText.Range] = [{ start: 0n, end: s32(title.count) }];
    <Text
        session={app.ui.session}
        props={{
            bounds: { x: bounds.x, y: bounds.y, width: bounds.width, height: half },
            text: title,
            size: AppFontSize(),
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignEnd,
            wrap: Wrap.TextWrapEllipsis
        }}
    />;
    <Text
        session={app.ui.session}
        props={{
            bounds: { x: bounds.x, y: bounds.y + half, width: bounds.width, height: half },
            text: detail,
            size: AppSmallFontSize(),
            class_name: MutedTextClass(),
            vertical_align: TextAlign.TextAlignStart,
            wrap: Wrap.TextWrapEllipsis
        }}
    />;
}

function WorkoutBuilderCheck(
    app: NativeRef<InnerBreeze>,
    key: u64,
    bounds: Rectangle,
    chosen: boolean
): void {
    let size = float32(AppScale(24n));
    let mark: Rectangle = {
        x: bounds.x + bounds.width - size - float32(AppScale(12n)),
        y: bounds.y + (bounds.height - size) / 2.0,
        width: size,
        height: size
    };
    <Box
        session={app.ui.session}
        props={{
            key: key,
            bounds: mark,
            fill: chosen ? StyleTokenColor("accent") : StyleTokenColor("surface"),
            border: StyleTokenColor(chosen ? "accent" : "text"),
            radius: size / 2.0
        }}
    />;
    if (chosen) {
        let dot = size / 3.0;
        <Box
            session={app.ui.session}
            props={{
                key: key + 1n,
                bounds: { x: mark.x + dot, y: mark.y + dot, width: dot, height: dot },
                fill: StyleTokenColor("surface"),
                radius: dot / 2.0
            }}
        />;
    }
}

function WorkoutBuilderPress(
    app: NativeRef<InnerBreeze>,
    row_index: s32,
    face: Rectangle,
    key: u64,
    label: string,
    selected: boolean
): boolean {
    let node = nativeAt(workout_builder.rows, row_index).node;
    if (workout_builder.choosing) {
        const rowClicked = Button({
            session: app.ui.session,
            props: {
                key: key,
                bounds: face,
                label: label,
                invisible: true,
                selected: selected
            }
        });
        if (rowClicked) {
            WorkoutBuilderTap(node);
        }
        return false;
    }
    const result = SortableItem({
        state: nativeRef(workout_builder.drag),
        widget: {
            session: app.ui.session,
            props: {
                key: key,
                row: row_index,
                bounds: face,
                label: label,
                now: HostSeconds(),
                touch: WorkoutBuilderTouch(),
                slop: float32(AppScale(6n))
            }
        }
    });
    if (result.clicked) {
        WorkoutBuilderTap(node);
    }
    return result.dropped && WorkoutBuilderDrop(row_index, result.pointer.y);
}

function WorkoutBuilderBlockFace(
    app: NativeRef<InnerBreeze>,
    row_index: s32,
    bounds: Rectangle,
    copy: s32,
    visible: boolean
): boolean {
    let row = nativeRef(nativeAt(workout_builder.rows, row_index));
    let plan = nativeRef(workout_builder.draft);
    let node = nativeRef(nativeAt(plan.nodes, row.node));
    let selected = row.node === workout_builder.selected && !workout_builder.choosing;
    let chosen = workout_builder.choosing && nativeAt(workout_builder.chosen, row.node);
    let key = Layout.KeyHash("workout/builder/block") + u64(row.node) * 8n;
    let name = WorkoutBuilderExercise(app, node.exercise);
    if (visible) {
        WorkoutBuilderCard(app, key, bounds, selected || chosen, "surface");
    }
    if (WorkoutBuilderPress(app, row_index, bounds, key + 1n, name, selected || chosen)) {
        return true;
    }
    if (!visible) {
        return false;
    }
    WorkoutBuilderBlockLabels(app, node, bounds, copy, name);
    if (workout_builder.choosing) {
        WorkoutBuilderCheck(app, key + 2n, bounds, chosen);
    }
    return false;
}

function WorkoutBuilderBlockLabels(
    app: NativeRef<InnerBreeze>,
    node: NativeRef<WorkoutNode>,
    bounds: Rectangle,
    copy: s32,
    name: string
): void {
    let pad = float32(AppScale(6n));
    let size = bounds.height - pad * 2.0;
    WorkoutBuilderThumbnail(
        app,
        node.exercise,
        node.variant,
        { x: bounds.x + pad, y: bounds.y + pad, width: size, height: size },
        copy,
        name
    );
    let left = bounds.x + pad * 2.0 + size;
    let right = workout_builder.choosing ? float32(AppScale(48n)) : pad * 2.0;
    let detail = WorkoutBuilderDetail(node);
    WorkoutBuilderLabels(
        app,
        { x: left, y: bounds.y + pad, width: bounds.x + bounds.width - left - right, height: size },
        name,
        detail
    );
    PackageFree(detail);
}

function WorkoutBuilderGroupFace(
    app: NativeRef<InnerBreeze>,
    row_index: s32,
    bounds: Rectangle
): boolean {
    let row = nativeRef(nativeAt(workout_builder.rows, row_index));
    let plan = nativeRef(workout_builder.draft);
    let node = nativeRef(nativeAt(plan.nodes, row.node));
    let selected = row.node === workout_builder.selected && !workout_builder.choosing;
    let chosen = workout_builder.choosing && nativeAt(workout_builder.chosen, row.node);
    let key = Layout.KeyHash("workout/builder/group") + u64(row.node) * 8n;
    let title_buffer = WorkoutBuilderTitleBuffer();
    let title = PackageText(WorkoutBuilderGroupTitle(node, nativeSlice(title_buffer)), "");
    if (selected || chosen) {
        WorkoutBuilderCard(app, key, bounds, true, "surface");
    }
    if (WorkoutBuilderPress(app, row_index, bounds, key + 1n, title, selected || chosen)) {
        PackageFree(title);
        return true;
    }
    WorkoutBuilderGroupLabels(app, row.node, bounds, title);
    PackageFree(title);
    if (workout_builder.choosing) {
        WorkoutBuilderCheck(app, key + 2n, bounds, chosen);
    }
    return false;
}

function WorkoutBuilderGroupLabels(
    app: NativeRef<InnerBreeze>,
    index: s32,
    bounds: Rectangle,
    title: string
): void {
    let pad = float32(AppScale(12n));
    let right = workout_builder.choosing ? float32(AppScale(48n)) : pad;
    let detail_buffer = WorkoutBuilderTextBuffer();
    WorkoutBuilderLabels(
        app,
        {
            x: bounds.x + pad,
            y: bounds.y + float32(AppScale(4n)),
            width: bounds.width - pad - right,
            height: bounds.height - float32(AppScale(8n))
        },
        title,
        WorkoutBuilderGroupDetail(index, nativeSlice(detail_buffer))
    );
}

function WorkoutBuilderGroupEnd(
    app: NativeRef<InnerBreeze>,
    row: NativeRef<WorkoutBuilderRow>,
    bounds: Rectangle
): void {
    let node = nativeRef(nativeAt(workout_builder.draft.nodes, row.node));
    let args: [FormatArg, FormatArg] = [{ number: node.repeats }, { number: node.rest }];
    let text_buffer = WorkoutBuilderTextBuffer();
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: bounds.x + float32(AppScale(12n)),
                y: bounds.y,
                width: bounds.width - float32(AppScale(24n)),
                height: bounds.height
            },
            text: WorkoutBuilderFormat(
                "workout_custom_group_end",
                nativeSlice(args),
                nativeSlice(text_buffer)
            ),
            size: AppSmallFontSize(),
            class_name: MutedTextClass(),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapEllipsis
        }}
    />;
}

function WorkoutBuilderSpin(
    app: NativeRef<InnerBreeze>,
    id: u64,
    bounds: Rectangle,
    label_key: string,
    value: s32,
    minimum: s32,
    maximum: s32,
    step: s32,
    value_key: string
): s32 {
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: bounds.x,
                y: bounds.y,
                width: bounds.width,
                height: float32(AppScale(24n))
            },
            text: LocaleText(label_key),
            size: AppSmallFontSize(),
            wrap: Wrap.TextWrapEllipsis
        }}
    />;
    let shown: [FormatArg] = [{ number: value }];
    let text_buffer = WorkoutBuilderTextBuffer();
    let value_text = WorkoutBuilderFormat(value_key, nativeSlice(shown), nativeSlice(text_buffer));
    let result = Spinbox({
        session: app.ui.session,
        props: {
            key: Layout.KeyHash("workout/builder/spin") + id,
            bounds: {
                x: bounds.x,
                y: bounds.y + float32(AppScale(24n)),
                width: bounds.width,
                height: bounds.height - float32(AppScale(24n))
            },
            label: LocaleText(label_key),
            min: minimum,
            max: maximum,
            step: step,
            value: value,
            value_text: value_text
        }
    });
    return result.changed ? result.value : value;
}

function WorkoutBuilderSettings(app: NativeRef<InnerBreeze>, index: s32, area: Rectangle): boolean {
    let plan = nativeRef(workout_builder.draft);
    let node = nativeRef(nativeAt(plan.nodes, index));
    let group = node.kind === WORKOUT_NODE_GROUP;
    let stride = WorkoutBuilderStride();
    let height = WorkoutBuilderControl();
    let spin_h = AppScale(24n) + height;
    let y: s32 = AppScale(6n);
    if (group) {
        let repeats = WorkoutBuilderSpin(
            app,
            1n,
            WorkoutBuilderSlice(area, y, spin_h, 0n, 2n),
            "workout_custom_rounds",
            node.repeats,
            1n,
            WORKOUT_PLAN_REPEAT_MAX,
            1n,
            "workout_custom_rounds_value"
        );
        if (WorkoutPlanAdjustRepeats(plan, index, repeats - node.repeats)) {
            WorkoutBuilderChanged();
        }
        let rest = WorkoutBuilderSpin(
            app,
            2n,
            WorkoutBuilderSlice(area, y, spin_h, 1n, 2n),
            "workout_custom_round_rest",
            node.rest,
            0n,
            WORKOUT_CUSTOM_REST_MAX,
            5n,
            "workout_custom_seconds_value"
        );
        if (WorkoutPlanAdjustRest(plan, index, rest - node.rest)) {
            WorkoutBuilderChanged();
        }
    } else {
        let seconds = WorkoutBuilderSpin(
            app,
            3n,
            WorkoutBuilderSlice(area, y, spin_h, 0n, 2n),
            "workout_custom_length",
            node.seconds,
            WORKOUT_CUSTOM_MIN_SECONDS,
            WORKOUT_CUSTOM_MAX_SECONDS,
            5n,
            "workout_custom_seconds_value"
        );
        if (WorkoutPlanAdjustSeconds(plan, index, seconds - node.seconds)) {
            WorkoutBuilderChanged();
        }
        let rest = WorkoutBuilderSpin(
            app,
            4n,
            WorkoutBuilderSlice(area, y, spin_h, 1n, 2n),
            "workout_custom_rest",
            node.rest,
            0n,
            WORKOUT_CUSTOM_REST_MAX,
            5n,
            "workout_custom_seconds_value"
        );
        if (WorkoutPlanAdjustRest(plan, index, rest - node.rest)) {
            WorkoutBuilderChanged();
        }
    }
    y += spin_h + AppScale(6n);
    if (!group && WorkoutBuilderVariantCount(node.exercise) > 1n) {
        let columns = WorkoutBuilderVariantCount(node.exercise);
        let column: s32 = s32(0n);
        for (let variant: s32 = s32(0n); variant <= 3n; variant += 1n) {
            if (!WorkoutBlockSupports(node.exercise, variant)) {
                continue;
            }
            const selectVariant = Button({
                session: app.ui.session,
                props: WorkoutBuilderButtonProps(
                    u64(30n + variant),
                    WorkoutBuilderSlice(area, y, height, column, columns),
                    LocaleText(WorkoutBuilderVariantKey(variant)),
                    false,
                    node.variant === variant
                )
            });
            if (
                selectVariant &&
                node.variant !== variant &&
                WorkoutPlanSetVariant(plan, index, variant)
            ) {
                WorkoutBuilderChanged();
            }
            column += 1n;
        }
        y += stride;
    }
    const moveUp = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            21n,
            WorkoutBuilderSlice(area, y, height, 0n, 2n),
            LocaleText("move_up_button")
        )
    });
    if (moveUp) {
        let moved = WorkoutBuilderShift(index, false);
        if (moved >= 0n) {
            workout_builder.selected = moved;
            WorkoutBuilderChanged();
            return true;
        }
    }
    const moveDown = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            22n,
            WorkoutBuilderSlice(area, y, height, 1n, 2n),
            LocaleText("move_down_button")
        )
    });
    if (moveDown) {
        let moved = WorkoutBuilderShift(index, true);
        if (moved >= 0n) {
            workout_builder.selected = moved;
            WorkoutBuilderChanged();
            return true;
        }
    }
    y += stride;
    let columns: s32 = group ? 3n : 2n;
    let column: s32 = s32(0n);
    if (group) {
        const ungroup = Button({
            session: app.ui.session,
            props: WorkoutBuilderButtonProps(
                23n,
                WorkoutBuilderSlice(area, y, height, 0n, 3n),
                LocaleText("workout_custom_ungroup")
            )
        });
        if (ungroup && WorkoutPlanUngroup(plan, index)) {
            workout_builder.selected = -1n;
            WorkoutBuilderChanged();
            return true;
        }
        column = 1n;
    }
    const duplicate = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            24n,
            WorkoutBuilderSlice(area, y, height, column, columns),
            LocaleText("workout_custom_duplicate"),
            !WorkoutBuilderFits(index)
        )
    });
    if (duplicate && WorkoutPlanDuplicate(plan, index)) {
        workout_builder.selected = WorkoutPlanEnd(plan, index);
        WorkoutBuilderChanged();
        return true;
    }
    const remove = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            25n,
            WorkoutBuilderSlice(area, y, height, column + 1n, columns),
            LocaleText("workout_custom_remove_block")
        )
    });
    if (remove && WorkoutPlanRemove(plan, index)) {
        workout_builder.selected = -1n;
        WorkoutBuilderChanged();
        return true;
    }
    return false;
}

function WorkoutBuilderTotals(app: NativeRef<InnerBreeze>, bounds: Rectangle): void {
    let times = WorkoutPlanTimesOf(nativeRef(workout_builder.draft));
    let text_buffer = WorkoutBuilderTextBuffer();
    let text = "";
    if (times.valid) {
        let total_buffer = WorkoutBuilderTextBuffer();
        let active_buffer = WorkoutBuilderTextBuffer();
        let args: [FormatArg, FormatArg, FormatArg] = [
            {
                text: WorkoutBuilderClock(times.total_seconds, nativeSlice(total_buffer)),
                is_text: true
            },
            {
                text: WorkoutBuilderClock(times.active_seconds, nativeSlice(active_buffer)),
                is_text: true
            },
            { number: times.steps }
        ];
        text = WorkoutBuilderFormat(
            "workout_custom_summary",
            nativeSlice(args),
            nativeSlice(text_buffer)
        );
    } else {
        text = LocaleText(
            workout_builder.draft.count > 0n ? "workout_custom_too_long" : "workout_custom_empty"
        );
    }
    <Text
        session={app.ui.session}
        props={{
            bounds: bounds,
            text: text,
            size: AppFontSize(),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapAuto
        }}
    />;
}

function WorkoutBuilderList(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    stride: s32,
    height: s32
): s32 {
    const newRoutine = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            2n,
            WorkoutBuilderSlice(area, 0n, height),
            LocaleText("workout_custom_new"),
            WorkoutBuilderFreeSlot() < 0n
        )
    });
    if (newRoutine) {
        WorkoutBuilderEdit(-1n);
        return WORKOUT_BUILDER_STAY;
    }
    let y = stride;
    for (let slot: s32 = s32(0n); slot < WORKOUT_CUSTOM_ROUTINE_LIMIT; slot += 1n) {
        if (!nativeAt(workout_builder.occupied, slot)) {
            continue;
        }
        let name = WorkoutBuilderNameBuffer();
        let label = WorkoutPlanName(
            nativeRef(nativeAt(workout_builder.slots, slot)),
            nativeSlice(name)
        );
        if (label.count === 0n) {
            label = LocaleText("workout_custom_unavailable");
        }
        const editRoutine = Button({
            session: app.ui.session,
            props: WorkoutBuilderButtonProps(
                u64(40n + slot),
                WorkoutBuilderSlice(area, y, height),
                label,
                nativeAt(workout_builder.slots, slot).count === 0n
            )
        });
        if (editRoutine) {
            WorkoutBuilderEdit(slot);
            return WORKOUT_BUILDER_STAY;
        }
        y += stride;
    }
    return WORKOUT_BUILDER_STAY;
}

function WorkoutBuilderHeading(app: NativeRef<InnerBreeze>, bounds: Rectangle, key: string): void {
    let text = LocaleText(key);
    let strong: [NativeText.Range] = [{ start: 0n, end: s32(text.count) }];
    <Text
        session={app.ui.session}
        props={{
            bounds: bounds,
            text: text,
            size: AppFontSize(),
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
}

function WorkoutBuilderPick(app: NativeRef<InnerBreeze>, area: Rectangle, bounds: Rectangle): void {
    let height = WorkoutBuilderControl();
    const backToEditor = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            3n,
            WorkoutBuilderSlice(area, 0n, height),
            LocaleText("workout_custom_blocks")
        )
    });
    if (backToEditor) {
        workout_builder.page = WORKOUT_BUILDER_EDITOR;
        return;
    }
    let insertion = WorkoutBuilderInsertionAt();
    let tile = WorkoutBuilderTile();
    let gap = AppScale(6n);
    let y = WorkoutBuilderStride();
    WorkoutBuilderHeading(
        app,
        WorkoutBuilderSlice(area, y, AppScale(30n)),
        "workout_custom_exercises"
    );
    y += AppScale(36n);
    for (let exercise: s32 = s32(0n); exercise < WORKOUT_MOVE_COUNT; exercise += 1n) {
        let tile_bounds = WorkoutBuilderSlice(area, y, tile);
        y += tile + gap;
        let node = WorkoutPlanExercise(exercise);
        let trial: WorkoutPlan = {};
        const fits = WorkoutBuilderTryInsert(insertion, node, nativeRef(trial));
        let key = Layout.KeyHash("workout/builder/pick") + u64(exercise) * 4n;
        let name = WorkoutBuilderExercise(app, exercise);
        // Every exercise stays reachable; only tiles in view draw their figure.
        let visible =
            tile_bounds.y + tile_bounds.height >= bounds.y &&
            tile_bounds.y <= bounds.y + bounds.height;
        if (visible) {
            WorkoutBuilderCard(app, key, tile_bounds, false, "surface");
        }
        const exerciseClicked = Button({
            session: app.ui.session,
            props: {
                key: key + 1n,
                bounds: tile_bounds,
                label: name,
                invisible: true,
                disabled: !fits
            }
        });
        if (exerciseClicked && fits) {
            WorkoutBuilderAcceptInsertion(insertion.slot, nativeRef(trial));
            return;
        }
        if (!visible) {
            continue;
        }
        let pad = float32(AppScale(6n));
        let size = tile_bounds.height - pad * 2.0;
        WorkoutBuilderThumbnail(
            app,
            exercise,
            node.variant,
            { x: tile_bounds.x + pad, y: tile_bounds.y + pad, width: size, height: size },
            0n,
            name
        );
        let left = tile_bounds.x + pad * 2.0 + size;
        let detail = WorkoutBuilderDetail(nativeRef(node));
        WorkoutBuilderLabels(
            app,
            {
                x: left,
                y: tile_bounds.y + pad,
                width: tile_bounds.x + tile_bounds.width - left - pad,
                height: size
            },
            name,
            detail
        );
        PackageFree(detail);
    }
    let heading = false;
    for (let saved: s32 = s32(0n); saved < WORKOUT_CUSTOM_ROUTINE_LIMIT; saved += 1n) {
        let routine = nativeRef(nativeAt(workout_builder.slots, saved));
        if (
            !nativeAt(workout_builder.occupied, saved) ||
            routine.count === 0n ||
            saved === workout_builder.slot
        ) {
            continue;
        }
        if (!heading) {
            WorkoutBuilderHeading(
                app,
                WorkoutBuilderSlice(area, y, AppScale(30n)),
                "workout_custom_library"
            );
            y += AppScale(36n);
            heading = true;
        }
        let tile_bounds = WorkoutBuilderSlice(area, y, tile);
        y += tile + gap;
        let trial: WorkoutPlan = {};
        const fits = WorkoutBuilderTryInsertRoutine(insertion, routine, nativeRef(trial));
        let key = Layout.KeyHash("workout/builder/pick/routine") + u64(saved) * 4n;
        WorkoutBuilderCard(app, key, tile_bounds, false, "surface");
        let name_buffer = WorkoutBuilderNameBuffer();
        let name = WorkoutPlanName(routine, nativeSlice(name_buffer));
        const routineClicked = Button({
            session: app.ui.session,
            props: {
                key: key + 1n,
                bounds: tile_bounds,
                label: name,
                invisible: true,
                disabled: !fits
            }
        });
        if (routineClicked && fits) {
            WorkoutBuilderAcceptInsertion(insertion.slot, nativeRef(trial));
            return;
        }
        let pad = float32(AppScale(6n));
        let size = tile_bounds.height - pad * 2.0;
        let first = nativeAt(routine.nodes, 0n);
        let cursor: s32 = s32(0n);
        while (
            cursor < routine.count &&
            nativeAt(routine.nodes, cursor).kind === WORKOUT_NODE_GROUP
        ) {
            cursor += 1n;
        }
        if (cursor < routine.count) {
            first = nativeAt(routine.nodes, cursor);
            WorkoutBuilderThumbnail(
                app,
                first.exercise,
                first.variant,
                { x: tile_bounds.x + pad, y: tile_bounds.y + pad, width: size, height: size },
                1n + saved,
                name
            );
        }
        let times = WorkoutPlanTimesOf(routine);
        let left = tile_bounds.x + pad * 2.0 + size;
        let total_buffer = WorkoutBuilderTextBuffer();
        let detail_buffer = WorkoutBuilderTextBuffer();
        let args: [FormatArg, FormatArg] = [
            {
                text: WorkoutBuilderClock(times.total_seconds, nativeSlice(total_buffer)),
                is_text: true
            },
            { number: times.steps }
        ];
        WorkoutBuilderLabels(
            app,
            {
                x: left,
                y: tile_bounds.y + pad,
                width: tile_bounds.x + tile_bounds.width - left - pad,
                height: size
            },
            name,
            WorkoutBuilderFormat(
                "workout_custom_routine_detail",
                nativeSlice(args),
                nativeSlice(detail_buffer)
            )
        );
    }
}

function WorkoutBuilderBlocks(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    top: s32,
    bounds: Rectangle
): boolean {
    let indent = WorkoutBuilderIndent();
    let copies = WorkoutBuilderPictureCopies();
    for (let row_index: s32 = s32(0n); row_index < workout_builder.row_count; row_index += 1n) {
        let row = nativeRef(nativeAt(workout_builder.rows, row_index));
        if (row.kind !== WORKOUT_BUILDER_ROW_GROUP || row.end < 0n) {
            continue;
        }
        // A group's frame holds its header, contents and end.
        let last = nativeRef(nativeAt(workout_builder.rows, row.end));
        let x = area.x + float32(row.depth * indent);
        let frame: Rectangle = {
            x: x,
            y: area.y + float32(top + row.y),
            width: area.width - float32(row.depth * indent),
            height: float32(last.y + last.height - row.y)
        };
        let fill = StyleTokenColor("accent");
        fill.a = u8(18n);
        let border = StyleTokenColor("accent");
        border.a = u8(110n);
        <Box
            session={app.ui.session}
            props={{
                key: Layout.KeyHash("workout/builder/frame") + u64(row.node),
                bounds: frame,
                fill: fill,
                border: border,
                radius: float32(AppScale(14n))
            }}
        />;
    }
    for (let row_index: s32 = s32(0n); row_index < workout_builder.row_count; row_index += 1n) {
        let row = nativeRef(nativeAt(workout_builder.rows, row_index));
        let inset = row.depth * indent;
        let face: Rectangle = {
            x: area.x + float32(inset),
            y: area.y + float32(top + row.y),
            width: area.width - float32(inset),
            height: float32(row.face)
        };
        nativeSet(workout_builder.sortable, row_index, {
            bounds: face,
            depth: row.depth,
            end: row.end,
            closes: row.kind === WORKOUT_BUILDER_ROW_END,
            fixed: row.kind === WORKOUT_BUILDER_ROW_END
        });
    }
    for (let row_index: s32 = s32(0n); row_index < workout_builder.row_count; row_index += 1n) {
        let row = nativeRef(nativeAt(workout_builder.rows, row_index));
        let face = nativeAt(workout_builder.sortable, row_index).bounds;
        let visible = face.y + face.height >= bounds.y && face.y <= bounds.y + bounds.height;
        if (row.kind === WORKOUT_BUILDER_ROW_BLOCK) {
            let node = nativeAt(workout_builder.draft.nodes, row.node);
            let picture = node.exercise * 4n + node.variant;
            let copy = nativeAt(copies, picture);
            nativeSet(copies, picture, copy + 1n);
            // The lifted block keeps its press while it is scrolled away.
            if (WorkoutBuilderBlockFace(app, row_index, face, copy, visible)) {
                return true;
            }
        } else if (row.kind === WORKOUT_BUILDER_ROW_GROUP) {
            if (WorkoutBuilderGroupFace(app, row_index, face)) {
                return true;
            }
        } else {
            WorkoutBuilderGroupEnd(app, row, face);
        }
        if (
            row.kind !== WORKOUT_BUILDER_ROW_END &&
            row.node === workout_builder.selected &&
            !workout_builder.choosing
        ) {
            let panel: Rectangle = {
                x: face.x,
                y: face.y + face.height,
                width: face.width,
                height: float32(row.height - row.face)
            };
            if (WorkoutBuilderSettings(app, row.node, panel)) {
                return true;
            }
        }
    }
    WorkoutBuilderLiftedRow(app);
    return false;
}

function WorkoutBuilderLiftedRow(app: NativeRef<InnerBreeze>): void {
    let drag = workout_builder.drag;
    if (!drag.active || !drag.lifted || drag.row < 0n || drag.row >= workout_builder.row_count) {
        return;
    }
    let drop = Sortable.Target(
        nativeSlice(workout_builder.sortable, 0n, workout_builder.row_count),
        drag.row,
        drag.pointer.y,
        float32(WorkoutBuilderIndent())
    );
    let row = nativeAt(workout_builder.rows, drag.row);
    let ghost = Sortable.Lifted(drag);
    let key = Layout.KeyHash("workout/builder/lifted");
    WorkoutBuilderCard(app, key, ghost, true, "surface");
    let node = nativeRef(nativeAt(workout_builder.draft.nodes, row.node));
    if (row.kind === WORKOUT_BUILDER_ROW_BLOCK) {
        WorkoutBuilderBlockLabels(
            app,
            node,
            ghost,
            WORKOUT_PLAN_NODE_LIMIT,
            WorkoutBuilderExercise(app, node.exercise)
        );
    } else {
        let title_buffer = WorkoutBuilderTitleBuffer();
        let title = PackageText(WorkoutBuilderGroupTitle(node, nativeSlice(title_buffer)), "");
        WorkoutBuilderGroupLabels(app, row.node, ghost, title);
        PackageFree(title);
    }
    // The landing place stays visible over the lifted block.
    let moved: WorkoutPlan = {};
    if (WorkoutBuilderDropped(drag.row, drop, nativeRef(moved))) {
        <SortableIndicator
            session={app.ui.session}
            key={Layout.KeyHash("workout/builder/drop")}
            drop={drop}
            color={StyleTokenColor("accent")}
            thickness={float32(AppScale(4n))}
            radius={float32(AppScale(12n))}
        />;
    }
}

function WorkoutBuilderToolbar(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    y: s32,
    height: s32
): boolean {
    if (workout_builder.choosing) {
        const grouped = WorkoutBuilderCanGroup();
        const groupBlocks = Button({
            session: app.ui.session,
            props: WorkoutBuilderButtonProps(
                8n,
                WorkoutBuilderSlice(area, y, height, 0n, 2n),
                LocaleText("workout_custom_group"),
                !grouped,
                true
            )
        });
        if (groupBlocks && grouped) {
            WorkoutBuilderGroupChosen();
            return true;
        }
        const cancelGrouping = Button({
            session: app.ui.session,
            props: WorkoutBuilderButtonProps(
                9n,
                WorkoutBuilderSlice(area, y, height, 1n, 2n),
                LocaleText("cancel_button")
            )
        });
        if (cancelGrouping) {
            WorkoutBuilderStopChoosing();
            return true;
        }
        return false;
    }
    const pickBlock = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            7n,
            WorkoutBuilderSlice(area, y, height, 0n, 2n),
            LocaleText("workout_custom_add_block"),
            workout_builder.draft.count >= WORKOUT_PLAN_NODE_LIMIT
        )
    });
    if (pickBlock) {
        workout_builder.page = WORKOUT_BUILDER_PICKER;
        workout_builder.picker_scroll = 0n;
        return true;
    }
    const chooseBlocks = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            10n,
            WorkoutBuilderSlice(area, y, height, 1n, 2n),
            LocaleText("workout_custom_select"),
            workout_builder.draft.count === 0n
        )
    });
    if (chooseBlocks) {
        WorkoutBuilderStartChoosing();
        return true;
    }
    return false;
}

function WorkoutBuilderEditor(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    bounds: Rectangle,
    ready: boolean
): s32 {
    let stride = WorkoutBuilderStride();
    let height = WorkoutBuilderControl();
    const backLabel = workout_builder.confirm_back
        ? "workout_custom_discard"
        : "workout_custom_library";
    const back = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            4n,
            WorkoutBuilderSlice(area, 0n, height),
            LocaleText(backLabel)
        )
    });
    if (back) {
        WorkoutBuilderBack();
        if (workout_builder.page === WORKOUT_BUILDER_LIBRARY) {
            return WORKOUT_BUILDER_STAY;
        }
    }
    if (
        WorkoutBuilderField(
            app,
            nativeRef(workout_builder.name),
            WORKOUT_BUILDER_NAME_FIELD,
            WorkoutBuilderSlice(area, stride, height),
            "workout_custom_name"
        )
    ) {
        WorkoutBuilderChanged();
    }
    WorkoutBuilderTotals(app, WorkoutBuilderSlice(area, stride * 2n, height));
    const can_play = WorkoutBuilderCanPlay();
    const save = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            5n,
            WorkoutBuilderSlice(area, stride * 3n, height, 0n, 2n),
            LocaleText("save_button"),
            !can_play
        )
    });
    if (save) {
        WorkoutBuilderSave();
    }
    const play = Button({
        session: app.ui.session,
        props: WorkoutBuilderButtonProps(
            6n,
            WorkoutBuilderSlice(area, stride * 3n, height, 1n, 2n),
            LocaleText("workout_custom_play"),
            !can_play || !ready,
            true
        )
    });
    if (play) {
        return WORKOUT_BUILDER_PLAY;
    }
    let status = WorkoutBuilderStatus();
    let toolbar = stride * 4n;
    if (status.count > 0n) {
        <Text
            session={app.ui.session}
            props={{
                bounds: WorkoutBuilderSlice(area, stride * 4n, height),
                text: LocaleText(status),
                size: AppSmallFontSize(),
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapAuto
            }}
        />;
        toolbar = stride * 5n;
    }
    if (WorkoutBuilderToolbar(app, area, toolbar, height)) {
        return WORKOUT_BUILDER_STAY;
    }
    WorkoutBuilderBlocks(app, area, WorkoutBuilderHeaderHeight(), bounds);
    return WORKOUT_BUILDER_STAY;
}

function WorkoutBuilderPage(
    app: NativeRef<InnerBreeze>,
    content: Rectangle,
    bounds: Rectangle,
    ready: boolean
): s32 {
    const full = s32(content.width);
    const width = full - AppScale(4n) * 2n;
    if (width <= 0n) {
        return WORKOUT_BUILDER_STAY;
    }
    const area: Rectangle = {
        x: content.x + float32((full - width) / 2n),
        y: content.y,
        width: float32(width),
        height: content.height
    };
    if (workout_builder.page === WORKOUT_BUILDER_LIBRARY) {
        return WorkoutBuilderList(app, area, WorkoutBuilderStride(), WorkoutBuilderControl());
    }
    if (workout_builder.page === WORKOUT_BUILDER_PICKER) {
        WorkoutBuilderPick(app, area, bounds);
        return WORKOUT_BUILDER_STAY;
    }
    return WorkoutBuilderEditor(app, area, bounds, ready);
}

export function WorkoutBuilderView(
    app: NativeRef<InnerBreeze>,
    bounds: Rectangle,
    ready: boolean
): s32 {
    const viewport = WorkoutBuilderScrollProps(bounds);
    // Update the next frame's drag scroll before drawing this frame's content.
    let action: s32 = s32(WORKOUT_BUILDER_STAY);
    const action_ref = nativeRef(action);
    const scroll = Scroll({
        session: app.ui.session,
        props: viewport.props,
        children: (scroll: NativeScroll.ScrollResult): void => {
            WorkoutBuilderScrollOffset(bounds, viewport.offset, scroll);

            nativeDeref(action_ref) = WorkoutBuilderPage(app, scroll.content, bounds, ready);
        }
    });
    if (!scroll.opened) {
        WorkoutBuilderScrollOffset(bounds, viewport.offset, scroll);
        return WORKOUT_BUILDER_STAY;
    }
    return action;
}
