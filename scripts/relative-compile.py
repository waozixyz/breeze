#!/usr/bin/env python3
"""Keep ThinLTO source identifiers independent of the checkout's location."""

import os
import sys


def main():
    command = sys.argv[1:]
    if not command:
        raise SystemExit("relative-compile: missing compiler command")

    # Clang's file-prefix maps normalize debug information and __FILE__, but
    # its LLVM source_filename still uses the compiler input verbatim. ThinLTO
    # hashes that name into promoted symbols and ultimately the ELF build ID.
    # CMake runs each compile from its build directory, whose relative layout
    # to the source is stable across release and F-Droid checkout locations.
    for index, argument in enumerate(command[:-1]):
        if argument == "-c" and os.path.isabs(command[index + 1]):
            command[index + 1] = os.path.relpath(command[index + 1])

    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
