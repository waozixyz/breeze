#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${ZIRAN_BIN:-"$repo/build/ziran-toolchain/bin/ziran"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

cat > "$work/app.zi" <<'ZI'
#import "locale_policy"

#program_export
Answer :: () -> s32 {
    languages: [7]LocaleLanguage
    languages[0] = LocaleLanguage.{"en", "English"}
    languages[1] = LocaleLanguage.{"pt-BR", "Português"}
    languages[2] = LocaleLanguage.{"fr", "Français"}
    languages[3] = LocaleLanguage.{"pt", "Português"}
    languages[4] = LocaleLanguage.{"zh", "中文"}
    languages[5] = LocaleLanguage.{"es", "Español"}
    languages[6] = LocaleLanguage.{"de", "Deutsch"}
    if LocaleRequestedCode("") != "en" ||
        LocaleRequestedCode("fr") != "fr" ||
        !LocaleHasEnglish(languages[:]) ||
        !LocaleContainsCode(languages[:], "pt-BR") ||
        LocaleContainsCode(languages[:], "ja") { return -1 }

    active: [1]LocaleEntry
    active[0] = LocaleEntry.{"greeting", "Olá"}
    base: [2]LocaleEntry
    base[0] = LocaleEntry.{"greeting", "Hello"}
    base[1] = LocaleEntry.{"bye", "Goodbye"}
    if LocaleResolveValue(active[:], base[:], "greeting") != "Olá" ||
        LocaleResolveValue(active[:], base[:], "bye") != "Goodbye" ||
        LocaleResolveValue(active[:], base[:], "missing") != "missing" {
        return -2
    }
    active_text: string = "[greeting]\nOlá\n---\n[empty]\n---\n"
    base_text: string = "[greeting]\nHello\n---\n[bye]\nGoodbye\n---\n"
    if LocaleResolveCatalog(active_text, base_text, "greeting") != "Olá" ||
        LocaleResolveCatalog(active_text, base_text, "bye") != "Goodbye" ||
        LocaleResolveCatalog(active_text, base_text, "empty") != "" ||
        LocaleResolveCatalog(active_text, base_text, "missing") != "missing" {
        return -5
    }

    if LocalePreferredCode(languages[:], "C:fr_FR.UTF-8;pt_BR@foo") != "fr" ||
        LocalePreferredCode(languages[:], "POSIX,pt_BR.UTF-8") != "pt-BR" ||
        LocalePreferredCode(languages[:], "es_AR;pt_PT") != "es" ||
        LocalePreferredCode(languages[:], "es_AR;fr_CA") != "es" ||
        LocalePreferredCode(languages[:], "pt__BR") != "pt-BR" ||
        LocalePreferredCode(languages[:], "zh-Hans-CN") != "zh" ||
        LocalePreferredCode(languages[:], "EN_us.UTF-8") != "en" ||
        LocalePreferredCode(languages[:], "de_DE@euro") != "de" ||
        LocalePreferredCode(languages[:], "xx") != "en" { return -3 }

    none: []LocaleLanguage = languages[:0]
    if LocaleHasEnglish(none) ||
        LocalePreferredCode(none, "fr") != "en" { return -4 }
    return 42
}
ZI

"$ziran" ir --root "$work" --module-path "$repo/src" \
    -o "$work/ir" "$work/app.zi"
for input in source saved; do
    if test "$input" = source; then
        source=$work/app.zi
        root=$work
        module_path=$repo/src
    else
        source=$work/ir/app.zir
        root=$work/ir
        module_path=$work/ir
    fi
    "$ziran" bundle --root "$root" --module-path "$module_path" \
        --entry app:Answer -o "$work/$input.zib" "$source"
    test "$("$ziran" run "$work/$input.zib")" = 42
    for target in c cpp go; do
        output=$work/$target-$input
        "$ziran" build --target="$target" \
            --root "$root" --module-path "$module_path" \
            -o "$output" "$source"
        if test "$target" = c; then
            cat > "$output/main.c" <<'C'
#include "app.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
            "${CC:-cc}" -std=c11 -I"$repo/build/packages/ziran/include" \
                -I"$output" "$output"/*.c -o "$output/app"
            "$output/app"
        elif test "$target" = cpp; then
            cat > "$output/main.cpp" <<'CPP'
#include "app.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
            "${CXX:-c++}" -std=c++17 -I"$repo/build/packages/ziran/include" \
                -I"$output" "$output"/*.cpp -o "$output/app"
            "$output/app"
        else
            cat > "$output/locale_test.go" <<'GO'
package ziran
import "testing"
func TestLocalePolicy(t *testing.T) {
    if App_Answer() != 42 { t.Fatal("locale policy") }
}
GO
            GO111MODULE=off go test "$output"/*.go
        fi
    done
done
cmp "$work/source.zib" "$work/saved.zib"
