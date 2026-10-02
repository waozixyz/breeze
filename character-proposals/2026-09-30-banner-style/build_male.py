#!/usr/bin/env python3
"""Render the two male counterparts from their saved painted atlases.

The approved female animations are reused without rendering them again.
Artwork generation is separate: the sunrise man reuses his approved drawing,
and the sage man was made with built-in imagegen. This script is offscreen.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "inbe_proposals_pipeline", HERE / "build_proposals.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register(pipeline):
    manifest = json.loads((HERE / "prompts.json").read_text())
    existing = {entry["id"]: entry for entry in manifest["concepts"]}
    entries = []
    for concept in pipeline.CONCEPTS:
        if concept.get("gender") != "male":
            entries.append(existing[concept["id"]])
            continue
        entry = dict(concept)
        source = HERE / "source" / (concept["id"] + "-generation.json")
        generation = json.loads(source.read_text())
        if "prompt" in generation:
            entry["prompt"] = generation["prompt"]
        else:
            entry["artwork_note"] = "Uses the approved archived male atlas and torso with joined necks and the saved built-in image_gen outfit edits. The archive retains model usage, but not the original atlas prompt."
        entry["source_generation"] = str(source.relative_to(HERE))
        entries.append(entry)
    manifest["concepts"] = entries
    manifest["revision"] = "2026-10-02: two approved women and two men with distinct rust-and-charcoal and indigo-and-sand outfits"
    manifest["outfit_edits"] = "source/outfit-edits-20261002.json"
    manifest["artwork_sources"] = [
        {
            "concepts": [entry["id"] for entry in entries[:3]],
            "tool": "OpenRouter",
            "model": pipeline.MODEL,
        },
        {
            "concepts": [entries[3]["id"]],
            "tool": "built-in image_gen",
            "source": entries[3]["source_generation"],
            "transparent_background": True,
        },
    ]
    for field in ("model", "route", "resolution", "aspect_ratio"):
        manifest.pop(field, None)
    (HERE / "prompts.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["prepare", "inspect", "render", "gif", "page", "all"]
    )
    parser.add_argument("--concept", type=int, choices=[3, 4])
    args = parser.parse_args()
    pipeline = load_pipeline()
    register(pipeline)
    concepts = [
        concept for concept in pipeline.CONCEPTS
        if concept.get("gender") == "male"
    ]
    if args.concept is not None:
        concepts = [pipeline.CONCEPTS[args.concept - 1]]
    if args.action in ("inspect", "render", "all"):
        for concept in concepts:
            pipeline.render(concept, inspect=args.action == "inspect")
    if args.action in ("gif", "all"):
        for concept in concepts:
            pipeline.export_gif(concept)
    if args.action in ("page", "all"):
        pipeline.review_page()


if __name__ == "__main__":
    main()
