/*
 * Locale -> font asset mapping + font file presence.
 *
 * Links the real Ziran FontAssetForLocale selector, so a change in the app
 * is actually what gets tested. Glyph coverage of the files themselves is
 * asserted separately by font_glyph_coverage_test.
 */

#include "app/font_assets.h"

#include <stdio.h>
#include <string.h>

#ifndef KRYON_DIR
#define KRYON_DIR "vendor/kryon"
#endif

typedef struct LocaleFontCase {
    const char *locale;
    const char *font;
} LocaleFontCase;

static int
file_exists(const char *path)
{
    FILE *fp = fopen(path, "rb");

    if(fp == NULL)
        return 0;
    fclose(fp);
    return 1;
}

int
main(void)
{
    static const LocaleFontCase cases[] = {
        {"en",      FONT_LATIN},
        {"cs",      FONT_LATIN},
        {"de",      FONT_LATIN},
        {"es",      FONT_LATIN},
        {"fr",      FONT_LATIN},
        {"id",      FONT_LATIN},
        {"it",      FONT_LATIN},
        {"pt",      FONT_LATIN},
        {"ru",      FONT_LATIN},
        {"zh",      FONT_SC},
        {"zh-TW",   FONT_TC},
        {"zh_Hant", FONT_TC},
        {"ja",      FONT_JP},
        {"ko",      FONT_KR},
        {NULL,      FONT_LATIN}
    };
    int failures = 0;

    for(size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        const char *locale = cases[i].locale ? cases[i].locale : "";
        String actual = FontAssetForLocale(StringView(locale, strlen(locale)));

        if(actual.data == NULL || actual.length != strlen(cases[i].font) ||
           memcmp(actual.data, cases[i].font, actual.length) != 0) {
            fprintf(stderr, "FAIL locale %s mapped to %s, expected %s\n",
                    cases[i].locale ? cases[i].locale : "(null)",
                    actual.data ? actual.data : "(null)", cases[i].font);
            failures++;
        }
        if(!file_exists(cases[i].font)) {
            fprintf(stderr, "FAIL missing font file %s\n", cases[i].font);
            failures++;
        }
    }

    if(failures != 0) {
        fprintf(stderr, "%d locale font failure(s)\n", failures);
        return 1;
    }

    printf("font locale tests passed\n");
    return 0;
}
