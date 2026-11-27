// The host paints the logical canvas before routing the active TSX screen.
// Picture windows use the surface token; the main viewport uses canvas.
import { Box } from "kryon/tsx/box";
import { StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { Session } from "kryon/session";

export function ApplicationCanvas(
    session: Session,
    bounds: Rectangle,
    pictureWindow: boolean
): void {
    const token = pictureWindow ? "surface" : "canvas";
    <Box session={session} props={{ bounds: bounds, fill: StyleTokenColor(token) }} />;
}
