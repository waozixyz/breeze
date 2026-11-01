#!/usr/bin/env python3
"""Validate and map bounded outputs for release-ready and the release gate."""
import re
import sys


def release_ready_output(requested="build/release-ready"):
    if not re.fullmatch(r"build/release-ready(?:-[a-z0-9][a-z0-9-]*)?", requested):
        raise ValueError("RELEASE_READY_OUTPUT must be build/release-ready or build/release-ready-NAME")
    if requested == "build/release-ready-phone":
        return requested
    return "build/release-ready"


if __name__ == "__main__":
    try:
        print(release_ready_output(sys.argv[1]))
    except ValueError as error:
        sys.exit(str(error))
