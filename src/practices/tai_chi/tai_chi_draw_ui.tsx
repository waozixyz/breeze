import { TaiChiDrawNewScreen } from "tai_chi_draw";
// Authored UI composition; native application state remains in tai_chi_draw.zi.
import * as NativeImage from "kryon/image";
import * as State_tai_chi_draw from "tai_chi_draw";
import { Rectangle } from "kryon/geometry";
import { Session } from "kryon/session";
import { Image } from "kryon/tsx/image";
import { FlagShiftLeft, FlagUnion } from "native_flags";
import {
    TAI_CHI_FLAT_FEATHER,
    TAI_CHI_FLAT_THINNEST,
    TaiChiFlatCacheBegin,
    TaiChiFlatCacheFind,
    TaiChiFlatCacheKeep
} from "tai_chi_draw";
import { TAI_CHI_FLAT_FILL, TaiChiFlatFrame } from "tai_chi_flat";
import { TaiChiFlatFanMesh, TaiChiFlatStripMesh } from "tai_chi_flat_mesh";
import { TaiChiClamp, TaiChiMax } from "tai_chi_math";
import { TaiChiFraming } from "tai_chi_rules";

export function TaiChiPaintFlatCachedView(
    session: Session,
    key: u64,
    digest: u64,
    area: Rectangle,
    alt_text: string,
    edge_path: string
): boolean {
    let found = TaiChiFlatCacheFind(key, area);
    if (digest === 0n || found < 0n) {
        return false;
    }
    let slot = &State_tai_chi_draw.tai_chi_flat_cache[found];
    if (!slot.stored || slot.digest !== digest) {
        return false;
    }
    State_tai_chi_draw.tai_chi_flat_cache_clock = State_tai_chi_draw.tai_chi_flat_cache_clock + 1n;
    slot.used = State_tai_chi_draw.tai_chi_flat_cache_clock;
    let screen = TaiChiDrawNewScreen();
    for (let at = s32(0n); at < slot.op_count; at += s32(1)) {
        let op = slot.ops[at];
        for (let point = s32(0n); point < op.count; point += s32(1)) {
            let kept = slot.points[op.first + point];
            screen[point] = { x: area.x + kept.x, y: area.y + kept.y };
        }
        let picture: NativeImage.Props = {};
        picture.key = key + u64(op.index);
        picture.bounds = area;
        picture.smooth = true;
        picture.alt_text = op.labelled ? alt_text : "";
        picture.asset_path = edge_path;
        picture.tint = op.tint;
        picture.mesh.columns = op.columns;
        picture.mesh.rows = op.count / op.columns;
        picture.mesh.points = screen[:op.count];
        <Image session={session} props={picture} />;
    }
    return true;
}

export function TaiChiPaintFlatEdgeView(
    session: Session,
    frame: *TaiChiFlatFrame,
    framing: TaiChiFraming,
    mirrored: boolean,
    area: Rectangle,
    key: u64,
    alt_text: string,
    edge_path: string,
    digest: u64 = 0n
): void {
    let keeping = TaiChiFlatCacheBegin(key, digest, area);
    let kept = keeping >= 0n;
    let pixels = float64(area.height) / framing.view_height;
    let middle_x = float64(area.x) + float64(area.width) / 2.0;
    let middle_y = float64(area.y) + float64(area.height) / 2.0;
    let mirror: float64 = 1.0;
    if (mirrored) {
        mirror = -1.0;
    }
    let screen = TaiChiDrawNewScreen();
    for (let index = s32(0n); index < frame.op_count; index += s32(1)) {
        let op = frame.ops[index];
        let points = frame.points[op.first:op.first + op.count];
        let count: s32 = 0n;
        let columns: s32 = 0n;
        if (op.kind === TAI_CHI_FLAT_FILL) {
            count = TaiChiFlatFanMesh(
                points,
                TAI_CHI_FLAT_FEATHER / pixels,
                screen[:]
            );
            columns = 4n;
        } else {
            let width = TaiChiMax(op.width, TAI_CHI_FLAT_THINNEST / pixels);
            count = TaiChiFlatStripMesh(points, width * 0.75, screen[:]);
            columns = 2n;
        }
        if (count === 0n) {
            continue;
        }
        for (let point = s32(0n); point < count; point += s32(1)) {
            screen[point].x = float32(middle_x + float64(screen[point].x) * pixels * mirror);
            screen[point].y = float32(
                middle_y - (float64(screen[point].y) - framing.view_center) * pixels
            );
        }
        let alpha = u32(TaiChiClamp(op.alpha, 0.0, 1.0) * 255.0 + 0.5);
        if (alpha === u32(0n)) {
            continue;
        }
        let labelled = index === frame.op_count - 1n;
        let tint = FlagUnion(FlagShiftLeft(op.color, u32(8n)), alpha);
        let picture: NativeImage.Props = {};
        picture.key = key + u64(index);
        picture.bounds = area;
        picture.smooth = true;
        picture.alt_text = labelled ? alt_text : "";
        picture.asset_path = edge_path;
        picture.tint = tint;
        picture.mesh.columns = columns;
        picture.mesh.rows = count / columns;
        picture.mesh.points = screen[:count];
        <Image session={session} props={picture} />;
        if (kept) {
            kept = TaiChiFlatCacheKeep(
                &State_tai_chi_draw.tai_chi_flat_cache[keeping],
                index,
                screen[:count],
                columns,
                tint,
                labelled,
                area
            );
        }
    }
    if (keeping >= 0n) {
        State_tai_chi_draw.tai_chi_flat_cache[keeping].stored = kept;
    }
}
