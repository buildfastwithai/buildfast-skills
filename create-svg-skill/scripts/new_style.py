#!/usr/bin/env python3
"""new_style.py - scaffold a new style for SVG Style Studio.

Adding a style takes three steps:
  1. python3 new_style.py --id vaporwave --name "Vaporwave" --family genre \
         --alias "vapor wave" --alias "aesthetic" --description "..." --file genre
     -> appends a filled-in TEMPLATE to styles/registry/genre.json (or creates a new
        registry file) and a reference stub section to styles/references/genre.md
  2. Edit the TODO fields in the JSON (palette, geometry, stroke, texture, composition,
     techniques, avoid, checks) and write the recipe in the reference stub.
  3. python3 route_style.py --lint      # must print 0 errors

Usage
  new_style.py --id ID --name NAME --family FAMILY [--alias A ...] [--extends PARENT]
               [--description TEXT] [--file REGISTRY_BASENAME] [--best-for illustration,poster]
  new_style.py --checks                 # list supported machine checks for the "checks" block

The template is deliberately full of TODO markers so lint (and you) notice incomplete entries.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtools import REFERENCE_DIR, REGISTRY_DIR, load_registry, slug  # noqa: E402
from route_style import KNOWN_CHECKS  # noqa: E402

CHECK_HELP = {
    "forbid_elements": "list of tags the style avoids, e.g. [\"filter\", \"circle\"]",
    "require_elements_any": "at least one of these tags must be present, e.g. [\"pattern\"]",
    "max_colors / min_colors": "distinct colour budget",
    "forbid_path_curves": "true -> only M/L/H/V/Z path commands (straight-edged styles)",
    "integer_coords": "true -> <rect> coordinates must be integers (grid styles)",
    "require_shape_rendering": "e.g. \"crispEdges\" on the root / >= 90% of shapes",
    "max_filters / min_filters": "filtered-element cap / required <filter> count",
    "max_gradients / min_gradients": "gradient count bounds",
    "min_elements / max_elements": "painted-element bounds (detail level)",
    "min_groups": "minimum <g> count (layering)",
    "require_text / forbid_text": "typography expected / avoided",
    "min_stroke_widths / max_stroke_widths": "line-hierarchy or consistency",
    "require_stroke / forbid_stroke": "outline-based vs fill-only",
    "require_linecap / require_linejoin": "e.g. \"round\"",
    "dark_base / light_base": "true -> first painted background must be dark / light",
    "allow_bleed": "true -> content may touch/exceed the canvas edge (patterns, full-bleed posters)",
}

TEMPLATE = {
    "id": None,
    "name": None,
    "family": None,
    "aliases": [],
    "keywords": ["TODO: weaker trigger words, e.g. typical subjects/motifs of this style"],
    "description": "TODO: one or two sentences describing the visual language, not just the colours.",
    "visual_characteristics": ["TODO: 3-5 concrete, checkable traits"],
    "palette": {"guidance": "TODO: base, accents, value structure, saturation rules.", "swatches": ["#111111", "#eeeeee"]},
    "geometry": "TODO: shape vocabulary, proportions, grids, corner treatment, symmetry, perspective.",
    "stroke": "TODO: widths, caps, joins, hierarchy, or 'none'.",
    "texture": "TODO: patterns, grain, halftone, imperfections.",
    "composition": "TODO: layout rules, focal strategy, negative space, layering/depth.",
    "typography": "TODO: type treatment or 'avoid text'.",
    "lighting_depth": "TODO: lighting model, shadows, depth cues.",
    "svg_techniques": ["TODO: concrete SVG constructions (patterns, gradients, masks, filters with parameters)"],
    "avoid": ["TODO: things that break the style"],
    "compatible_with": [],
    "conflicts_with": [],
    "best_for": ["illustration"],
    "detail_level": "medium",
    "checks": {"min_elements": 10},
    "reference": None,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id")
    ap.add_argument("--name")
    ap.add_argument("--family")
    ap.add_argument("--alias", action="append", default=[])
    ap.add_argument("--extends")
    ap.add_argument("--description")
    ap.add_argument("--file", help="registry file basename to append to (default: the family name)")
    ap.add_argument("--best-for", dest="best_for")
    ap.add_argument("--checks", action="store_true", help="list supported check keys and exit")
    a = ap.parse_args()

    if a.checks:
        for k, v in CHECK_HELP.items():
            print("%-40s %s" % (k, v))
        missing = KNOWN_CHECKS - {t.strip() for k in CHECK_HELP for t in k.split("/")}
        if missing:
            print("(undocumented: %s)" % ", ".join(sorted(missing)))
        return
    if not (a.id and a.name and a.family):
        ap.error("--id, --name and --family are required")
    sid = slug(a.id)
    reg = load_registry()
    if sid in reg:
        sys.exit("style id %r already exists (%s)" % (sid, reg[sid]["_file"]))
    if a.extends and a.extends not in reg:
        sys.exit("--extends %r is not a known style" % a.extends)

    entry = json.loads(json.dumps(TEMPLATE))
    entry["id"], entry["name"], entry["family"] = sid, a.name, a.family
    entry["aliases"] = a.alias or [a.name.lower()]
    if a.description:
        entry["description"] = a.description
    if a.extends:
        entry["extends"] = a.extends
    if a.best_for:
        entry["best_for"] = [x.strip() for x in a.best_for.split(",") if x.strip()]
    base = slug(a.file or a.family)
    entry["reference"] = "%s.md#%s" % (base, sid)

    reg_file = REGISTRY_DIR / (base + ".json")
    items = []
    if reg_file.exists():
        data = json.loads(reg_file.read_text(encoding="utf-8"))
        items = data["styles"] if isinstance(data, dict) else data
    items.append(entry)
    reg_file.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ref_file = REFERENCE_DIR / (base + ".md")
    stub = (
        "\n---\n\n## %s {#%s}\n\n"
        "**Layer stack**: TODO `back` → `mid` → `front` → `overlay`\n\n"
        "**Design moves**\n- TODO\n\n"
        "**Recipe**\n```svg\n<!-- TODO: working SVG snippet of the style's signature technique -->\n```\n\n"
        "**QA checklist**\n- [ ] TODO\n"
    ) % (a.name, sid)
    if ref_file.exists():
        ref_file.write_text(ref_file.read_text(encoding="utf-8").rstrip() + "\n" + stub, encoding="utf-8")
    else:
        ref_file.write_text("# %s styles\n\nReference for: %s.\n%s" % (base.replace("-", " ").title(), a.name, stub), encoding="utf-8")

    print("added %r to %s and a reference stub to %s" % (sid, reg_file, ref_file))
    print("next: fill in every TODO, add compatible_with/conflicts_with, then run: python3 route_style.py --lint")


if __name__ == "__main__":
    main()
