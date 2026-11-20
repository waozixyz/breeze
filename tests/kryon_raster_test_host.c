#include "kryon_raster_test_backend.h"

#include <assert.h>

/* These tests submit paint and inspect the retained tree without a renderer. */
void RasterLine(Rectangle line, Color color) { (void)line; (void)color; assert(0); }
void RasterRoundedRectangle(Rectangle bounds, float radius, int32_t segments, Color color) {
    (void)bounds; (void)radius; (void)segments; (void)color; assert(0);
}
void RasterRoundedRectangleOutline(Rectangle bounds, float radius, int32_t segments,
    float width, Color color) {
    (void)bounds; (void)radius; (void)segments; (void)width; (void)color; assert(0);
}
void RasterText(String value, int32_t x, int32_t y, int32_t font, Color color) {
    (void)value; (void)x; (void)y; (void)font; (void)color; assert(0);
}
void RasterTextClipped(String value, int32_t x, int32_t y, int32_t font,
    Color color, Rectangle clip) {
    (void)value; (void)x; (void)y; (void)font; (void)color; (void)clip; assert(0);
}
void RasterTextRotated(String value, int32_t x, int32_t y, int32_t font,
    Color color, Rectangle clip, Vector2 origin, float rotation,
    Rectangle outer_clip, bool outer_clipped, bool emphasis, bool italic) {
    (void)value; (void)x; (void)y; (void)font; (void)color; (void)clip;
    (void)origin; (void)rotation; (void)outer_clip; (void)outer_clipped;
    (void)emphasis; (void)italic; assert(0);
}
void RasterTriangles(Slice points, Color color) { (void)points; (void)color; assert(0); }
void RasterImage(String path, uint32_t texture, Rectangle source,
    Rectangle destination, Rectangle clip, Vector2 origin, float rotation,
    float radius, Color tint) {
    (void)path; (void)texture; (void)source; (void)destination;
    (void)clip; (void)origin; (void)rotation; (void)radius; (void)tint;
    assert(0);
}
void RasterImageMesh(String path, uint32_t texture, Rectangle source,
    Slice points, int32_t columns, int32_t rows, Rectangle clip, Color tint) {
    (void)path; (void)texture; (void)source; (void)points;
    (void)columns; (void)rows; (void)clip; (void)tint;
    assert(0);
}

int32_t
MeasureGlyphWidth(String value, int32_t font, String typeface)
{
    (void)typeface;
    return (int32_t)value.length * font / 2;
}

int32_t
MeasureGlyphLineHeight(int32_t font, String typeface)
{
    (void)typeface;
    return font;
}
