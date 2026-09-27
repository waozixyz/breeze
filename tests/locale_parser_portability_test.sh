#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${ZIRAN_BIN:-"$repo/build/ziran-toolchain/bin/ziran"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

cat > "$work/app.zi" <<'ZI'
#import "locale_parser"

#program_export
Answer :: () -> s32 {
    entries: [4]LocaleEntrySpan
    data: [128]u8
    parsed: LocaleParseResult = LocaleParseEntries(
        "[hello]\r\nWorld\r\nAgain\r\n---\n[bye]\nBye\n---\n[hello]\nNew\n---\n",
        entries[:], data[:])
    if !parsed.complete || parsed.count != 2 ||
        !LocaleSpanEquals(data[:], entries[0].key, "hello") ||
        !LocaleSpanEquals(data[:], entries[0].value, "New") ||
        !LocaleSpanEquals(data[:], entries[1].key, "bye") ||
        !LocaleSpanEquals(data[:], entries[1].value, "Bye") { return -1 }

    parsed = LocaleParseEntries("[discard]\nLost\n[keep]\nFirst\n\nLast",
        entries[:], data[:])
    if !parsed.complete || parsed.count != 1 ||
        !LocaleSpanEquals(data[:], entries[0].key, "keep") ||
        !LocaleSpanEquals(data[:], entries[0].value, "First\n\nLast") {
        return -2
    }
    parsed = LocaleParseEntries("[empty]\n---\n", entries[:], data[:])
    if !parsed.complete || parsed.count != 1 ||
        !LocaleSpanEquals(data[:], entries[0].value, "") { return -3 }

    languages: [3]LocaleLanguageSpan
    listed: LocaleParseResult = LocaleParseLanguages(
        "# comment\r\nen|English\npt-BR|Português\nbad|\n|bad\n",
        languages[:], data[:])
    if !listed.complete || listed.count != 2 ||
        !LocaleSpanEquals(data[:], languages[0].code, "en") ||
        !LocaleSpanEquals(data[:], languages[0].label, "English") ||
        !LocaleSpanEquals(data[:], languages[1].code, "pt-BR") ||
        !LocaleSpanEquals(data[:], languages[1].label, "Português") {
        return -4
    }

    no_entries: []LocaleEntrySpan = entries[:0]
    short_data: []u8 = data[:1]
    if LocaleParseEntries("[a]\nx\n---", no_entries, data[:]).complete ||
        LocaleParseEntries("[a]\nx\n---", entries[:], short_data).complete ||
        LocaleParseLanguages("en|English", languages[:], short_data).complete {
        return -5
    }
    found: LocaleTextResult = LocaleFindText(
        "[hello]\nWorld\n---\n[bye]\nBye\n---\n[hello]\nNew\n---\n",
        "hello")
    if !found.found || found.text != "New" { return -6 }
    found = LocaleFindText("[empty]\n---\n", "empty")
    if !found.found || found.text != "" { return -7 }
    found = LocaleFindText("[discard]\nLost\n[keep]\nFirst\n\nLast",
        "keep")
    if !found.found || found.text != "First\n\nLast" { return -8 }
    found = LocaleFindText("[missing]\nvalue\n---", "absent")
    if found.found || found.text != "" { return -9 }
    found = LocaleFindText("[line]\nOne\r\nTwo\n---", "line")
    if !found.found || found.text != "One\r\nTwo" { return -10 }
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
func TestLocaleParser(t *testing.T) {
    if App_Answer() != 42 { t.Fatal("locale parser") }
}
GO
            GO111MODULE=off go test "$output"/*.go
        fi
    done
done
cmp "$work/source.zib" "$work/saved.zib"
