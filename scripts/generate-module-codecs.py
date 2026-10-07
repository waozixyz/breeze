#!/usr/bin/env python3
"""Emit typed Ziran value codecs for the cell protocol, with schema-sized storage."""

from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
schema = {}
for file in [
    *sorted((root / "src/cells").glob("*_types.zi")),
    root / "src/core/types.zi",
    root / "src/practices/patterns/patterns_types.zi",
    root / "src/practices/sun_salutation/sun_salutation_rules.zi",
    root / "build/packages/kryon/src/ui/drawing_props.zi",
]:
    for name, body in re.findall(
        r"(\w+)\s*::\s*struct\s*\{([^{}]*)\}", file.read_text()
    ):
        fields = re.findall(r"^\s*(\w+)\s*:\s*([^\n;]+)", body, re.M)
        schema[name] = [(n, re.sub(r"\s+", "", t.split("//")[0])) for n, t in fields]
constants = {"CountSize": 4, "MaxRounds": 12}
roots = [
    "LumiMessage",
    "InbeMessage",
    "DiaryMessage",
    "DiaryFileResult",
    "ListsMessage",
    "ListsMutation",
    "ListsMutationResult",
    "HabitsMessage",
    "PracticeMessage",
]
needed = []


def discover(t):
    if t.startswith("["):
        discover(t[t.index("]") + 1 :])
        return
    if t in schema and t not in needed:
        for _, sub in schema[t]:
            discover(sub)
        needed.append(t)


for t in roots:
    discover(t)
lines = [
    "// Generated from protocol records by scripts/generate-module-codecs.py.",
    "// No native application pointers cross the portable module boundary.",
    *[
        f'#import, file "{name}_types.zi";'
        for name in ["module", "lists", "habits", "practice", "inbe", "diary", "lumi"]
    ],
    '#import "bundle_host"',
    '#import "byte_text_linux"',
    '#import "drawing_props"',
    '#import, file "../core/types.zi";',
    '#import, file "../practices/patterns/patterns_types.zi";',
    '#import, file "../practices/sun_salutation/sun_salutation_rules.zi";',
    "",
    "using HostValueKind;",
    "",
]


def dims(t):
    return [
        (constants.get(n, int(n) if n.isdigit() else 0))
        for n in re.findall(r"\[([^]]+)\]", t)
    ]


def elemtype(t):
    return re.sub(r"^\[[^]]+\]", "", t)


def scalar(t):
    return (
        "HostString"
        if t == "string"
        else (
            "HostReal"
            if t.startswith("float")
            else "HostUnsigned" if t.startswith("u") else "HostInteger"
        )
    )


# Each codec owns its recursive fields/arrays. Strings borrow the caller's storage.
for t in needed:
    lines += [f"{t}Codec :: struct {{", f"    fields: [{len(schema[t])}]HostField"]
    for n, sub in schema[t]:
        if sub in needed:
            lines += [f"    {n}: {sub}Codec"]
        elif sub.startswith("["):
            ds = dims(sub)
            if len(ds) > 1:
                lines += [f"    {n}_rows: [{ds[0]}]HostValue"]
            lines += [
                f"    {n}_elements: " + "".join(f"[{d}]" for d in ds) + "HostValue"
            ]
    lines += [
        "}",
        "",
        f"Encode{t} :: (data: {t}, codec: *{t}Codec) -> HostValue {{",
        "    value: HostValue",
        "    value.kind = cast(s32)HostRecord",
        f'    value.type_name = "{t}".data',
        "    value.fields = *codec.fields[0]",
        f"    value.field_count = {len(schema[t])}",
    ]
    for i, (n, sub) in enumerate(schema[t]):
        target = f"codec.fields[{i}].value"
        lines += [f'    codec.fields[{i}].name = "{n}".data']
        if sub in needed:
            lines += [f"    {target} = Encode{sub}(data.{n}, *codec.{n})"]
        elif sub.startswith("["):
            ds = dims(sub)
            base = re.sub(r"\[[^]]+\]", "", sub)
            canonical = "".join(f"[{d}]" for d in ds) + base
            lines += [
                f"    {target}.kind = cast(s32)HostArray",
                f'    {target}.type_name = "{canonical}".data',
                f"    {target}.length = {ds[0]}",
                f"    {target}.elements = *codec.{n}_"
                + ("rows[0]" if len(ds) > 1 else "elements[0]"),
                "    {",
                "        i: s32 = 0",
                f"        while i < {ds[0]} {{",
            ]
            if len(ds) > 1:
                row = f"codec.{n}_rows[i]"
                lines += [
                    f"            {row}.kind = cast(s32)HostArray",
                    f'            {row}.type_name = "[{ds[1]}]{base}".data',
                    f"            {row}.length = {ds[1]}",
                    f"            {row}.elements = *codec.{n}_elements[i][0]",
                    "            j: s32 = 0",
                    f"            while j < {ds[1]} {{",
                    f'                codec.{n}_elements[i][j] = ModuleScalar("{base}", cast(s64)data.{n}[i][j])',
                    "                j += 1",
                    "            }",
                ]
            else:
                lines += [
                    f'            codec.{n}_elements[i] = ModuleScalar("{base}", cast(s64)data.{n}[i])'
                ]
            lines += ["            i += 1", "        }", "    }"]
        elif sub == "string":
            lines += [
                f"    {target}.kind = cast(s32)HostString",
                f'    {target}.type_name = "string".data',
                f"    {target}.data = data.{n}.data",
                f"    {target}.length = cast(usize)data.{n}.count",
            ]
        elif sub.startswith("float"):
            lines += [
                f"    {target}.kind = cast(s32)HostReal",
                f'    {target}.type_name = "{sub}".data',
                f"    {target}.real = cast(float64)data.{n}",
            ]
        else:
            lines += [
                f'    {target} = ModuleScalar("{sub}", '
                + (
                    f"ifx data.{n} then 1 else 0)"
                    if sub == "bool"
                    else f"cast(s64)data.{n})"
                )
            ]
    lines += [
        "    return value",
        "}",
        "",
        f"Decode{t} :: (value: HostValue) -> {t} {{",
        f"    data: {t}",
    ]
    for i, (n, sub) in enumerate(schema[t]):
        v = f"value.fields[{i}].value"
        if sub in needed:
            lines += [f"    data.{n} = Decode{sub}({v})"]
        elif sub.startswith("["):
            ds = dims(sub)
            base = re.sub(r"\[[^]]+\]", "", sub)
            lines += ["    {", "        i: s32 = 0", f"        while i < {ds[0]} {{"]
            if len(ds) > 1:
                lines += [
                    "            j: s32 = 0",
                    f"            while j < {ds[1]} {{",
                    f"                data.{n}[i][j] = cast({base}){v}.elements[i].elements[j].bits",
                    "                j += 1",
                    "            }",
                ]
            else:
                lines += [
                    f"            data.{n}[i] = cast({base}){v}.elements[i]."
                    + ("bits" if base.startswith("u") else "integer")
                ]
            lines += ["            i += 1", "        }", "    }"]
        elif sub == "string":
            lines += [
                f"    data.{n} = TextFromBytes(BytesFromPointer({v}.data, cast(u64){v}.length))"
            ]
        elif sub == "bool":
            lines += [f"    data.{n} = {v}.integer != 0"]
        else:
            lines += [
                f"    data.{n} = cast({sub}){v}."
                + (
                    "real"
                    if sub.startswith("float")
                    else "bits" if sub.startswith("u") else "integer"
                )
            ]
    lines += ["    return data", "}", ""]
# Check every borrowed native value before any decoder can dereference it.
for t in needed:
    lines += [
        f"Valid{t} :: (value: HostValue) -> bool {{",
        f'    if value.kind != cast(s32)HostRecord || TextFromCString(value.type_name) != "{t}" ||',
        f"    value.field_count != {len(schema[t])} || value.fields == null {{",
        "        return false",
        "    }",
    ]
    for i, (n, sub) in enumerate(schema[t]):
        v = f"value.fields[{i}].value"
        lines += [
            f'    if TextFromCString(value.fields[{i}].name) != "{n}" {{',
            "        return false",
            "    }",
        ]
        if sub in needed:
            lines += [f"    if !Valid{sub}({v}) {{", "        return false", "    }"]
        elif sub.startswith("["):
            ds = dims(sub)
            base = re.sub(r"\[[^]]+\]", "", sub)
            canonical = "".join(f"[{d}]" for d in ds) + base
            lines += [
                f'    if !ModuleArrayValid({v}, "{canonical}", {ds[0]}) {{',
                "        return false",
                "    }",
                "    {",
                "        i: s32 = 0",
                f"        while i < {ds[0]} {{",
            ]
            if len(ds) > 1:
                lines += [
                    f'            if !ModuleArrayValid({v}.elements[i], "[{ds[1]}]{base}", {ds[1]}) {{',
                    "                return false",
                    "            }",
                    "            j: s32 = 0",
                    f"            while j < {ds[1]} {{",
                    f'                if !ModuleScalarValid({v}.elements[i].elements[j], "{base}", cast(s32){scalar(base)}) {{',
                    "                    return false",
                    "                }",
                    "                j += 1",
                    "            }",
                ]
            else:
                lines += [
                    f'            if !ModuleScalarValid({v}.elements[i], "{base}", cast(s32){scalar(base)}) {{',
                    "                return false",
                    "            }",
                ]
            lines += ["            i += 1", "        }", "    }"]
        else:
            lines += [
                f'    if !ModuleScalarValid({v}, "{sub}", cast(s32){scalar(sub)}) {{',
                "        return false",
                "    }",
            ]
    lines += ["    return true", "}", ""]
lines += [
    "ModuleScalarValid :: (value: HostValue, type_name: string, kind: s32) -> bool {",
    "    if value.kind != kind || TextFromCString(value.type_name) != type_name {",
    "        return false",
    "    }",
    "    if kind == cast(s32)HostString {",
    "        return value.length == 0 || value.data != null",
    "    }",
    "    return true",
    "}",
    "",
    "ModuleArrayValid :: (value: HostValue, type_name: string, count: usize) -> bool {",
    "    return value.kind == cast(s32)HostArray && TextFromCString(value.type_name) == type_name &&",
    "        value.length == count && value.elements != null",
    "}",
    "",
]
lines += [
    "ModuleScalar :: (type_name: string, number: s64) -> HostValue {",
    "    value: HostValue",
    "    value.type_name = type_name.data",
    "    value.integer = number",
    "    value.bits = cast(u64)number",
    "    value.kind = ifx type_name[0] == cast(u8)117 then cast(s32)HostUnsigned else cast(s32)HostInteger",
    "    return value",
    "}",
    "",
]
lines += [
    "ModuleTextData :: (text: string) -> *u8 {",
    "    descriptor := cast(*TextDescriptor)(*text)",
    "    return descriptor.data",
    "}",
    "",
]
source = "\n".join(lines)
source = re.sub(r'("[^"\n]+"|data\.\w+|type_name)\.data', r"ModuleTextData(\1)", source)
(root / "src/cells/value_codec.zi").write_text(source)
