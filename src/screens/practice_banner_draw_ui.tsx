// Authored UI composition; native application state remains in practice_banner_draw.zi.
import * as NativeBannerLayout from "kryon/layout";
import * as State_practice_banner_draw from "practice_banner_draw";
import { LocalNowHost } from "app_clock_host";
import { AssetGeneration, AssetRead } from "assets";
import { BitmapImageRelease } from "kryon/bitmap_image";
import { Rectangle } from "kryon/geometry";
import { ImageFit } from "kryon/image_props";
import { Session } from "kryon/session";
import { Box as BannerBox } from "kryon/tsx/box";
import { Image as BannerImage } from "kryon/tsx/image";
import { practice_banner_air, practice_banner_update } from "practice_banner_draw";
import { PracticeBannerTick } from "practice_banner_motion";
import {
    PracticeBannerSceneFor,
    PracticeBannerSkyView,
    PracticeBannerViewFor,
    PracticeBannerViewOverlap
} from "practice_banner_scene";
import { PracticeSkyAt } from "practice_banner_sky";
import { PracticeSteamView } from "practice_banner_steam";

export function PracticeBannerDrawBack(
    session: Session,
    asset: string,
    bounds: Rectangle,
    now: float64,
    visible: boolean,
    reduced_motion: boolean
): boolean {
    let state = nativeRef(State_practice_banner_draw.practice_banner_draw);
    state.tick = PracticeBannerTick(nativeRef(state.motion), asset, now, visible, reduced_motion);
    if (state.session.slot !== session.slot || state.session.epoch !== session.epoch) {
        BitmapImageRelease(state.session, state.sky);
        BitmapImageRelease(state.session, state.steam);
        state.sky = {};
        state.steam = {};
        state.shown = false;
        state.session = session;
    }
    let generation = AssetGeneration();
    if (state.asset !== asset || state.asset_generation !== generation) {
        state.asset = asset;
        state.asset_generation = generation;
        state.scene = PracticeBannerSceneFor(asset);
        state.layered =
            state.scene.landscape.count > 0n &&
            AssetRead(state.scene.landscape).found &&
            AssetRead(state.scene.character).found;
        state.asked.revision = state.asked.revision + 1n;
        state.air_painted = false;
        state.shown = false;
    }
    if (!state.layered || !visible) {
        return false;
    }
    if (!state.day_known) {
        let local = LocalNowHost();
        state.day_started =
            float64(s64(local.hour) * 3600n + s64(local.minute) * 60n + s64(local.second)) - now;
        state.day_known = true;
    }
    practice_banner_update(state, session, bounds, now);
    state.wants_frames = state.tick > 0n || !state.shown;
    let view = PracticeBannerViewFor(bounds.width, bounds.height);
    let sky_view = PracticeBannerSkyView(view, state.scene.sky);
    let sky_bounds: Rectangle = {
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height * float32(sky_view.height / view.height)
    };
    if (state.shown) {
        <BannerImage
            session={session}
            props={{
                key: NativeBannerLayout.KeyHash("practice/banner-live-sky"),
                bounds: sky_bounds,
                texture: state.sky,
                smooth: true
            }}
        />;
    } else {
        let sky = PracticeSkyAt(state.scene.sky, state.asked.clock, state.asked.seconds, view);
        <BannerBox
            session={session}
            props={{
                key: NativeBannerLayout.KeyHash("practice/banner-air-waiting"),
                bounds: sky_bounds,
                fill: practice_banner_air(sky.zenith),
                fill_bottom: practice_banner_air(sky.horizon),
                has_fill_bottom: true
            }}
        />;
    }
    <BannerImage
        session={session}
        props={{
            key: NativeBannerLayout.KeyHash("practice/banner-landscape"),
            bounds: bounds,
            asset_path: state.scene.landscape,
            fit: ImageFit.ImageFitCover,
            tint: 0xffffffffn
        }}
    />;
    return true;
}

export function PracticeBannerDrawFront(session: Session, bounds: Rectangle): void {
    let state = nativeRef(State_practice_banner_draw.practice_banner_draw);
    <BannerImage
        session={session}
        props={{
            key: NativeBannerLayout.KeyHash("practice/banner-character"),
            bounds: bounds,
            asset_path: state.scene.character,
            fit: ImageFit.ImageFitCover,
            tint: 0xffffffffn
        }}
    />;
    if (state.scene.steam.count === 0n || state.steam.id === 0n) {
        return;
    }
    let view = PracticeBannerViewFor(bounds.width, bounds.height);
    let shown = PracticeBannerViewOverlap(view, PracticeSteamView(state.scene.steam));
    if (shown.width <= 0.0 || shown.height <= 0.0) {
        return;
    }
    <BannerImage
        session={session}
        props={{
            key: NativeBannerLayout.KeyHash("practice/banner-steam"),
            bounds: {
                x: bounds.x + bounds.width * float32((shown.left - view.left) / view.width),
                y: bounds.y + bounds.height * float32((shown.top - view.top) / view.height),
                width: bounds.width * float32(shown.width / view.width),
                height: bounds.height * float32(shown.height / view.height)
            },
            texture: state.steam,
            smooth: true
        }}
    />;
}
