#include "metrics_link_behavior.h"
#include "font_metrics.h"

#include <assert.h>
#include <string.h>

int32_t MeasureGlyphWidth(String value, int32_t font, String typeface)
{
    assert(typeface.length == 2 && memcmp(typeface.data, "ui", 2) == 0);
    return (int32_t)(value.length * (size_t)font / 2);
}

int32_t MeasureGlyphLineHeight(int32_t font, String typeface)
{
    (void)typeface;
    return font;
}

int main(void)
{
    assert(Answer() == 42);
    return 0;
}
