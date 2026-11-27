import { Session } from "kryon/session";
import { Rectangle } from "kryon/geometry";
import { Image } from "kryon/tsx/image";
import { LoadingIndicator } from "kryon/tsx/loading_indicator";
import { TaiChiFraming } from "tai_chi_rules";
import { TaiChiSolved, TaiChiRig } from "tai_chi_solve";
import { PracticeFigurePlacement } from "practice_figure_draw";
import { PracticeFigurePrepare } from "practice_figure_draw";

export function PracticeFigureDrawModelView(
    session: Session,
    solved: NativeRef<TaiChiSolved>,
    rig: NativeRef<TaiChiRig>,
    framing: TaiChiFraming,
    man: boolean,
    mirrored: boolean,
    area: Rectangle,
    key: u64,
    alt_text: string,
    seconds: float64,
    digest: u64,
    placement: PracticeFigurePlacement
): boolean {
    const presentation = PracticeFigurePrepare(
        session,
        solved,
        rig,
        framing,
        man,
        mirrored,
        area,
        key,
        alt_text,
        seconds,
        digest,
        placement
    );
    if (presentation.loading) {
        <LoadingIndicator
            session={session}
            props={{ key: key, bounds: area, now: presentation.now, scale: 1.0 }}
        />;
    } else if (presentation.available) {
        <Image session={session} props={presentation.image} />;
    }
    return presentation.available;
}
