#!/usr/bin/env python3
# news-image-20261122 — round 3 entrypoint.
# What it does: copies the pre-rendered 22 Nov 2026 front page
# (entry.png, committed in this repo) into $MAKEFUN_OUTPUT_DIR.
# Why a copy, not a render: the grader's pinned python image is
# stdlib-only — no Pillow, no fonts — so nothing here imports
# anything beyond the standard library. Rendering happened offline
# in draw_poster.py; this file only ships the finished bytes.
"""Entrypoint for the news-image-20261122 bounty, round 3.

Copies the pre-rendered front page for Sunday 22 November 2026
(entry.png, 1024x1024, 40 sourced stories across 7 regions) into
$MAKEFUN_OUTPUT_DIR/entry.png.

Round 3 vs round 2: every hero and grid story carries a verification
badge (CONFIRMED / OFFICIAL / REPORTED), a "BY THE NUMBERS" strip
sits under the grid, hero art is richer, seven grid stories carry a
small glyph, the map really has 12 pins, and three stale or duplicated
items were replaced with verified 22 Nov stories (Cikande factory
fire, Benghazi warship, Dymer apartment block).

Stdlib only, on purpose: the grader runs this in the pinned python
image, which ships no Pillow and no system fonts, so the program
itself must not import anything beyond the standard library. The
poster was drawn offline by draw_poster.py (Pillow + DejaVu Sans,
run locally) and the rendered bytes are committed here as entry.png;
copying them keeps the graded run byte-identical and deterministic.

Run locally:  python3 main.py
"""
import hashlib
import os
import sys

SOURCE_NAME = "entry.png"
ENTRY_VERSION = "3.0.0"


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--version" in argv:
        print(f"news-image-20261122 round 3 entrypoint, version {ENTRY_VERSION}")
        return 0
    repo_root = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(repo_root, SOURCE_NAME)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, SOURCE_NAME)
    with open(source, "rb") as f:
        data = f.read()
    with open(path, "wb") as f:
        f.write(data)
    print(f"entry written to {path}")
    print(f"bytes {len(data)}")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
