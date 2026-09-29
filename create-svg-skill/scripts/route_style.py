#!/usr/bin/env python3
"""route_style.py - map a natural-language request to styles, modifiers, mode
and asset type, and print the design brief Claude should follow.

Usage
  route_style.py "Create a fox in ukiyo-e style"          resolve + brief
  route_style.py "pixel art with a horror aesthetic" --json
  route_style.py --menu                                    concise style menu (ask the user with this)
  route_style.py --list                                    all ids / names / aliases
  route_style.py --show ukiyo-e                            full brief for one style
  route_style.py --compat cyberpunk-neon pixel-art         blend plan for a pair
  route_style.py --lint                                    validate the whole registry

Output fields (--json)
  needs_style   true -> no style could be inferred: show the menu and ASK the user
  ambiguous     true -> several unrelated styles matched a vague phrase: ask which
  styles        [{id, role: primary|secondary|accent, matched}]
  modifiers     [{id, phrase, effect}]
  mode          single | multi | convert
  source        none | svg | raster        (what the user handed over, if anything)
  asset         illustration | icon | logo | poster | infographic | pattern | ...
  count         requested number of variants (multi mode)
  blend_plan    how compatible styles are combined (structure vs surface ownership)
  validate_cmd  the validate_svg.py invocation to run afterwards
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtools import REFERENCE_DIR, REGISTRY_DIR, SKILL_DIR, load_registry, slug  # noqa: E402

MODIFIERS_FILE = SKILL_DIR / "styles" / "modifiers.json"

REQUIRED_FIELDS = [
    "id", "name", "family", "aliases", "description", "visual_characteristics", "palette",
    "geometry", "stroke", "texture", "composition", "typography", "lighting_depth",
    "svg_techniques", "avoid", "best_for", "reference",
]
ASSET_TYPES = OrderedDict([
    ("logo", ["logo", "logotype", "wordmark", "emblem", "monogram", "brand mark", "crest", "badge"]),
    ("icon", ["icon", "icon set", "glyph", "pictogram", "favicon", "app icon"]),
    ("poster", ["poster", "flyer", "cover", "key art", "banner", "billboard", "album art", "book cover", "postcard"]),
    ("infographic", ["infographic", "chart", "diagram", "timeline", "data viz", "flowchart", "explainer"]),
    ("pattern", ["pattern", "wallpaper", "texture tile", "seamless", "background tile"]),
    ("sticker", ["sticker", "die cut", "die-cut", "patch"]),
    ("character", ["character", "mascot", "avatar", "portrait", "creature"]),
    ("scene", ["scene", "landscape", "cityscape", "skyline", "interior", "environment", "city", "street", "forest", "seascape"]),
])
NUM_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


# ---------------------------------------------------------------------------
def norm(text):
    t = text.lower()
    t = t.replace("&", " and ").replace("’", "'")
    t = re.sub(r"[/_\-–—]", " ", t)
    t = re.sub(r"[^a-z0-9+ '\.]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def phrase_re(p):
    p = norm(p)
    return re.compile(r"(?<![a-z0-9])" + re.escape(p).replace(r"\ ", r"\s+") + r"(?![a-z0-9])")


def load_modifiers():
    if not MODIFIERS_FILE.exists():
        return []
    return json.loads(MODIFIERS_FILE.read_text(encoding="utf-8"))["modifiers"]


class Router:
    def __init__(self):
        self.reg = load_registry()
        self.mods = load_modifiers()
        self.alias_index = []  # (regex, phrase_len_words, style_id, phrase)
        self.kw_index = []
        for sid, s in self.reg.items():
            phrases = set([s["name"], sid] + s.get("aliases", []))
            for ph in phrases:
                n = norm(ph)
                if n:
                    self.alias_index.append((phrase_re(n), len(n.split()), sid, n))
            for kw in s.get("keywords", []):
                self.kw_index.append((phrase_re(kw), sid, norm(kw)))
        self.weak_index = []
        for sid, s in self.reg.items():
            for ph in s.get("weak_aliases", []):
                n = norm(ph)
                if n:
                    self.weak_index.append((phrase_re(n), sid, n))
        self.alias_index.sort(key=lambda x: (-len(x[3]), x[3]))
        self.mod_index = []
        for m in self.mods:
            for tr in m["triggers"]:
                self.mod_index.append((phrase_re(tr), m, norm(tr)))
        self.mod_index.sort(key=lambda x: -len(x[2]))

    # ------------------------------------------------------------------
    def find_styles(self, text):
        """Strong (alias/name) matches with spans; longest match wins overlaps.
        Returns list of dicts in order of appearance."""
        taken = []  # spans
        found = []
        for rx, nwords, sid, ph in self.alias_index:
            for m in rx.finditer(text):
                span = m.span()
                if any(not (span[1] <= a or span[0] >= b) for a, b in taken):
                    continue
                found.append({"id": sid, "matched": ph, "span": span})
        # group ids that matched the very same span (e.g. '8 bit' -> pixel-art + retro-8bit)
        by_span = OrderedDict()
        for f in sorted(found, key=lambda f: f["span"]):
            by_span.setdefault(f["span"], []).append(f)
        results = []
        used = []
        for span, group in sorted(by_span.items(), key=lambda kv: (-(kv[0][1] - kv[0][0]), kv[0][0])):
            if any(not (span[1] <= a or span[0] >= b) for a, b in used):
                continue
            used.append(span)
            results.append((span, group))
        results.sort(key=lambda r: r[0][0])
        out = []
        for span, group in results:
            # when several styles share the very same phrase, the style that lists it
            # earliest in its aliases is primary (see README: adding aliases)
            def rank(g):
                al = [norm(a) for a in self.reg[g["id"]].get("aliases", [])]
                return al.index(g["matched"]) if g["matched"] in al else -1
            for g in sorted(group, key=rank):
                out.append(g)
        # weak aliases: generic words that are usually SUBJECT descriptors ("luxury hotel",
        # "futuristic motorcycle"). Accepted only when nothing stronger matched, or with
        # explicit style context ("luxury style", "+ luxury", "with a luxury touch").
        for rx, sid, ph in self.weak_index:
            for m in rx.finditer(text):
                span = m.span()
                if any(not (span[1] <= a or span[0] >= b) for a, b in used):
                    continue
                before, after = text[max(0, span[0] - 16):span[0]], text[span[1]:span[1] + 18]
                ctx = bool(re.search(r"(\+|\bplus\b|\bx\b|\bmeets\b|\bmixed with\b|\bblended with\b|\bwith an?\b)\s*$", before)) or \
                    bool(re.match(r"\s*(style|aesthetic|look|feel|vibe|theme|design|branding|finish|touch|accents?)\b", after))
                if ctx or not out:
                    out.append({"id": sid, "matched": ph, "span": span, "weak": not ctx})
                    used.append(span)
        return out, used

    def keyword_candidates(self, text, exclude_spans):
        scores = {}
        for rx, sid, kw in self.kw_index:
            for m in rx.finditer(text):
                if any(not (m.span()[1] <= a or m.span()[0] >= b) for a, b in exclude_spans):
                    continue
                scores.setdefault(sid, []).append(kw)
        ranked = sorted(scores.items(), key=lambda kv: (-len(set(kv[1])), kv[0]))
        return [(sid, sorted(set(kws))) for sid, kws in ranked]

    def find_modifiers(self, text, style_spans):
        mods, seen = [], set()
        for rx, m, tr in self.mod_index:
            for hit in rx.finditer(text):
                s = hit.span()
                if any(not (s[1] <= a or s[0] >= b) for a, b in style_spans):
                    continue
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                mods.append({"id": m["id"], "phrase": tr, "effect": m["effect"]})
        return mods

    # ------------------------------------------------------------------
    def detect_mode(self, text):
        count = None
        multi = False
        m = re.search(r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:different\s+|distinct\s+|various\s+)?(?:visual\s+)?(?:art\s+)?(?:styles?|versions?|variations?|looks?|takes?)\b", text)
        if m:
            v = m.group(1)
            count = int(v) if v.isdigit() else NUM_WORDS[v]
            multi = True
        if re.search(r"\b(several|multiple|many|all|each|every)\s+(?:different\s+)?styles?\b|\bdifferent\s+styles\b|\bstyle\s+(?:comparison|sampler|grid|sheet)\b|\bcompare\s+styles\b|\bin\s+(?:these|those)\s+styles\b|\bstyle\s+variations\b", text):
            multi = True
        source = "none"
        convert = False
        if re.search(r"\.svg\b|\b(this|the|my|attached|existing|above|following)\s+(?:svg|vector)\b", text):
            source = "svg"
        elif re.search(r"\.(png|jpe?g|webp|gif|bmp)\b|\b(this|the|my|attached|uploaded)\s+(image|photo|picture|screenshot|drawing|sketch|png|jpg|jpeg)\b", text):
            source = "raster"
        if re.search(r"\b(convert|restyle|re style|transform|turn|make)\s+(?:this|the|my|it|that)\b.*?\b(into|to|look|style|like|as)\b", text) or re.search(r"\bconvert\b|\brestyle\b|\bre style\b|\bin the style of\b.*\b(this|attached)\b", text):
            convert = source != "none" or bool(re.search(r"\b(convert|restyle|re style)\b", text))
        if source != "none" and re.search(r"\b(look like|into a|into an|as a|as an|to a|to an|style)\b", text):
            convert = True
        mode = "multi" if multi else ("convert" if convert else "single")
        return mode, count, source

    def detect_asset(self, text):
        for asset, words in ASSET_TYPES.items():
            for w in words:
                if phrase_re(w).search(text):
                    return asset
        return "illustration"

    # ------------------------------------------------------------------
    def resolve(self, prompt):
        text = norm(prompt)
        hits, spans = self.find_styles(text)
        mode, count, source = self.detect_mode(text)
        asset = self.detect_asset(text)
        # unique ids in order
        ids = []
        for h in hits:
            if h["id"] not in [i["id"] for i in ids]:
                ids.append({"id": h["id"], "matched": h["matched"], "span": h["span"], "weak": h.get("weak", False)})
        # a specialised style (extends X) already carries X's rules: drop the parent
        parents = {self.reg[i["id"]].get("extends") for i in ids if self.reg[i["id"]].get("extends")}
        ids = [i for i in ids if i["id"] not in parents]
        # an explicit LIST of 3+ styles ("pixel art, ukiyo-e, cyberpunk and blueprint") is a
        # multi-style request, not a blend (blends use "+", "with", "meets", "x", "mixed with")
        if mode == "single" and len(ids) >= 3:
            ordered = sorted((i for i in ids if i["span"] != (0, 0)), key=lambda i: i["span"][0])
            sep = re.compile(r"^\s*(,|,?\s*and|,?\s*or|vs\.?|versus|&|/)?\s*$")
            if len(ordered) >= 3 and all(sep.match(text[a["span"][1]:b["span"][0]]) for a, b in zip(ordered, ordered[1:])):
                mode = "multi"
                count = count or len(ordered)
        # multi-id for one phrase => same-phrase group
        same_phrase = OrderedDict()
        for h in ids:
            same_phrase.setdefault(h["span"], []).append(h)
        ambiguous = False
        candidates = []
        if not ids:
            cands = self.keyword_candidates(text, spans)
            if cands:
                top = len(cands[0][1])
                best = [c for c in cands if len(c[1]) == top][:3]
                if top >= 2 and len(best) == 1:
                    ids = [{"id": best[0][0], "matched": "+".join(best[0][1]), "span": (0, 0)}]
                elif top >= 1:
                    ambiguous = True
                    candidates = [{"id": c[0], "keywords": c[1]} for c in cands[:4]]
        mods = self.find_modifiers(text, spans)
        # roles
        styles = []
        aesthetic_secondary = bool(re.search(r"\b(with|plus|and)\s+(?:an?\s+|the\s+)?[a-z0-9 ']{0,30}?\b(aesthetic|vibe|mood|feel|flavou?r|theme|influences?|touches?|accents?|palette|lighting|atmosphere)\b", text))
        role_order = ["primary", "secondary", "accent"]
        if mode == "multi":
            styles = [{"id": h["id"], "role": "variant", "matched": h["matched"]} for h in ids]
        else:
            for i, h in enumerate(ids[:3]):
                styles.append({"id": h["id"], "role": role_order[min(i, 2)], "matched": h["matched"]})
                if h.get("weak"):
                    styles[-1]["weak"] = True
        # style + style from ONE phrase (e.g. '8 bit'): the child/specialised style leads
        for grp in same_phrase.values():
            if len(grp) > 1:
                pass
        # a child style implies its parent (retro-8bit extends pixel-art)
        res = {
            "prompt": prompt,
            "mode": mode,
            "count": count,
            "source": source,
            "asset": asset,
            "styles": styles,
            "modifiers": mods,
            "needs_style": not styles and not ambiguous and mode != "multi",
            "ambiguous": ambiguous,
            "candidates": candidates,
            "aesthetic_phrase": aesthetic_secondary,
            # only a generic word matched ("luxury hotel", "futuristic motorcycle"): probably a subject
            # descriptor, not a style request -> confirm before committing
            "confirm_style": bool(styles) and mode != "multi" and all(x.get("weak") for x in styles),
        }
        # multi mode with no (or one) explicit style: choose a diverse set
        if mode == "multi" and len(styles) < 2:
            n = max(count or 5, len(styles))
            pool = self.diverse(n, asset, [s["id"] for s in styles])
            res["multi_styles"] = pool
        elif mode == "multi":
            res["multi_styles"] = [s["id"] for s in styles]
        # in multi mode each style is separate (not a blend)
        if mode != "multi":
            res["blend_plan"] = self.blend_plan([s["id"] for s in styles]) if len(styles) > 1 else []
        res["validate_cmd"] = self.validate_cmd(res)
        res["subject_hint"] = self.subject_hint(text, [i["id"] for i in ids], mods, asset)
        res["file_names"] = self.file_names(res)
        return res

    # ------------------------------------------------------------------
    def diverse(self, n, asset, already):
        """Pick n styles spread over families, preferring styles that suit the asset."""
        fams = OrderedDict()
        for sid, s in self.reg.items():
            fams.setdefault(s["family"], []).append(sid)
        picks = list(already)
        # preference order inside families: styles listing the asset type in best_for first
        def pref(sid):
            bf = self.reg[sid].get("best_for", [])
            return (0 if asset in bf or "illustration" in bf and asset in ("scene", "character") else 1, sid)
        # round-robin across families in a fixed, contrast-friendly order
        order = ["pixel-retro", "east-asian", "digital-glossy", "craft", "technical", "decorative-eras", "print", "genre", "comics", "core-modern"]
        fam_names = [f for f in order if f in fams] + [f for f in fams if f not in order]
        idx = {f: 0 for f in fam_names}
        while len(picks) < n:
            progressed = False
            for f in fam_names:
                cand = sorted(fams[f], key=pref)
                while idx[f] < len(cand) and cand[idx[f]] in picks:
                    idx[f] += 1
                if idx[f] < len(cand):
                    picks.append(cand[idx[f]])
                    idx[f] += 1
                    progressed = True
                    if len(picks) >= n:
                        break
            if not progressed:
                break
        return picks[:n]

    def conflicts(self, a, b):
        A, B = self.reg[a], self.reg[b]
        return b in A.get("conflicts_with", []) or a in B.get("conflicts_with", [])

    def compatible(self, a, b):
        A, B = self.reg[a], self.reg[b]
        return b in A.get("compatible_with", []) or a in B.get("compatible_with", [])

    def blend_plan(self, ids):
        if len(ids) < 2:
            return []
        p = self.reg[ids[0]]
        lines = []
        lines.append("PRIMARY %s owns STRUCTURE: geometry, stroke rules, composition, typography, level of detail, and every hard check in its brief." % p["name"])
        for sid in ids[1:]:
            s = self.reg[sid]
            rel = "conflicts" if self.conflicts(ids[0], sid) else ("is a known-good pairing" if self.compatible(ids[0], sid) else "has no declared relationship")
            lines.append("SECONDARY %s (%s with %s)" % (s["name"], rel, p["name"]))
            if s.get("as_secondary"):
                lines.append("  behaves as: " + s["as_secondary"])
            else:
                lines.append("  contributes SURFACE + MOOD only: palette character (%s), lighting, texture, atmosphere, motifs and decorative vocabulary. It does NOT override the primary's geometry, stroke, or level-of-detail rules." % s["palette"]["guidance"].split(".")[0])
            pc, sc = p.get("checks", {}), s.get("checks", {})
            forb = set(pc.get("forbid_elements", []))
            if forb and (sc.get("min_filters") or sc.get("min_gradients")):
                lines.append("  primary forbids <%s>: emulate the secondary's glow/gradient/soft effects with hard-edged stacked shapes at stepped opacities instead." % ", ".join(sorted(forb)))
            if pc.get("max_colors"):
                lines.append("  primary caps the palette at %d colours: fit the secondary's hues INTO that budget." % pc["max_colors"])
            if self.conflicts(ids[0], sid):
                lines.append("  CONFLICT: import only the secondary's colour mood and motifs; drop its rendering techniques where they break the primary's rules.")
        lines.append("Sanity test: cover the palette - the drawing style must still read as %s; cover the drawing - the mood must still read as %s." % (p["name"], ", ".join(self.reg[i]["name"] for i in ids[1:])))
        return lines

    def validate_cmd(self, res):
        if res["mode"] == "multi":
            return "validate_svg.py <file>.svg --style <that file's style id>   (run once per output file)"
        if not res["styles"]:
            return "validate_svg.py <file>.svg"
        return "validate_svg.py <file>.svg --style %s" % res["styles"][0]["id"]

    FILLER = (r"please|can you|could you|i want|i need|i d like|give me|make me|make|create|generate|draw|design|produce|build|"
              r"an?|the|svg|vector|illustration|artwork|art|style|styled|version|versions|in|of|for|but|with|and|plus|different|same|"
              r"styles|aesthetic|this|that|these|those|image|picture|photo|it|my|attached|uploaded|look|looks|like|convert|restyle|"
              r"turn|transform|into|to|as|on|from|or|vs|versus|\d+|two|three|four|five|six|seven|eight|nine|ten|several|multiple|various|each|every|some")

    def subject_hint(self, text, style_ids, mods, asset=None):
        """Best-effort subject phrase: the request minus style phrases, modifier words,
        asset nouns and filler. Works on the normalised (lowercase) text."""
        t = " " + text + " "
        phrases = set()
        seen = set()
        stack = list(style_ids)
        while stack:
            sid = stack.pop()
            if sid in seen or sid not in self.reg:
                continue
            seen.add(sid)
            st = self.reg[sid]
            phrases.update([st["name"], sid] + st.get("aliases", []) + st.get("weak_aliases", []))
            if st.get("extends"):
                stack.append(st["extends"])
        spans = []
        for ph in phrases:
            for m in phrase_re(ph).finditer(t):
                spans.append(m.span())
        spans.sort()
        merged = []
        for sp in spans:
            if merged and sp[0] <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], sp[1]))
            else:
                merged.append(sp)
        out, pos = [], 0
        for a0, b0 in merged:
            out.append(t[pos:a0])
            out.append(" ")
            pos = b0
        out.append(t[pos:])
        t = "".join(out)
        mod_ids = {m["id"] for m in mods}
        for m in self.mods:
            if m["id"] in mod_ids:
                for tr in m["triggers"]:
                    t = phrase_re(tr).sub(" ", t)
        words = [w for ws in ASSET_TYPES.values() for w in ws]
        for w in sorted(words, key=len, reverse=True):
            t = phrase_re(w).sub(" ", t)
        t = re.sub(r"(?<![a-z0-9])(" + self.FILLER + r")(?![a-z0-9])", " ", t)
        t = re.sub(r"[\+\.,:;'\"]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t or None

    def file_names(self, res):
        base = slug(res["subject_hint"] or "artwork")[:40] or "artwork"
        if res["mode"] == "multi":
            ids = res.get("multi_styles", [])
            return [base + ".svg"] + ["%s-%s.svg" % (base, i) for i in ids]
        if res["styles"]:
            return ["%s-%s.svg" % (base, "-".join(s["id"] for s in res["styles"]))]
        return [base + ".svg"]

    # ------------------------------------------------------------------
    def menu(self):
        fams = OrderedDict()
        for sid, s in self.reg.items():
            fams.setdefault(s["family"], []).append(s)
        titles = {
            "core-modern": "Clean & modern", "pixel-retro": "Pixel & retro games", "digital-glossy": "Digital, glossy & 3D",
            "craft": "Handmade & illustrative", "comics": "Comics & manga", "east-asian": "East Asian traditions",
            "decorative-eras": "Historic & decorative", "print": "Print & street", "technical": "Technical & data",
            "genre": "Cinematic & genre",
        }
        out = ["Pick a style (or combine, e.g. \"cyberpunk + minimalist\"; or say \"5 styles\" for a comparison set):", ""]
        for fam, items in fams.items():
            out.append("%s: %s" % (titles.get(fam, fam.title()), " · ".join(s["name"] for s in items)))
        return "\n".join(out)

    def brief(self, sid, depth=0):
        s = self.reg[sid]
        out = []
        parent = s.get("extends")
        if parent and parent in self.reg and depth < 3:
            out.append(self.brief(parent, depth + 1))
            out.append("")
        h = "#" * 2 if depth == 0 else "#" * 2
        out.append("%s Style brief: %s (%s)%s" % (h, s["name"], s["id"], "  [extends %s: parent rules apply, these specialise them]" % parent if parent else ""))
        out.append(s["description"])
        def bullets(title, items):
            out.append("**%s**" % title)
            for i in items:
                out.append("- " + i)
        bullets("Visual characteristics", s["visual_characteristics"])
        out.append("**Palette**: %s" % s["palette"]["guidance"] + ("  Swatches: " + " ".join(s["palette"].get("swatches", [])) if s["palette"].get("swatches") else ""))
        for key, label in (("geometry", "Geometry"), ("stroke", "Stroke"), ("texture", "Texture"), ("composition", "Composition"), ("typography", "Typography"), ("lighting_depth", "Lighting & depth")):
            out.append("**%s**: %s" % (label, s[key]))
        bullets("SVG techniques", s["svg_techniques"])
        bullets("Avoid", s["avoid"])
        if s.get("checks"):
            out.append("**Automated checks** (validate_svg.py --style %s): %s" % (sid, ", ".join("%s=%s" % kv for kv in s["checks"].items())))
        out.append("**Deep reference**: styles/references/%s" % s["reference"])
        return "\n".join(out)

    def format_resolution(self, res, with_brief):
        L = []
        L.append("# Routing result")
        L.append("- mode: **%s**%s   asset: **%s**   source: **%s**" % (res["mode"], " (n=%d)" % res["count"] if res.get("count") else "", res["asset"], res["source"]))
        if res["subject_hint"]:
            L.append("- subject (best guess): %s" % res["subject_hint"])
        if res["needs_style"]:
            L.append("- style: **NOT SPECIFIED** -> ask the user; do not pick one yourself.\n")
            L.append(self.menu())
            return "\n".join(L)
        if res.get("confirm_style"):
            L.append("- style: **WEAK MATCH** (only the generic word '%s') -> one-line check with the user: use %s, or pick from the menu (`--menu`)?" % (res["styles"][0]["matched"], self.reg[res["styles"][0]["id"]]["name"]))
        if res["ambiguous"]:
            L.append("- style: **AMBIGUOUS** -> ask which one the user means (offer these, plus the menu on request):")
            for c in res["candidates"]:
                L.append("    - %s (%s) via: %s" % (self.reg[c["id"]]["name"], c["id"], ", ".join(c["keywords"])))
            return "\n".join(L)
        if res["mode"] == "multi":
            L.append("- variants: " + ", ".join(res["multi_styles"]))
            L.append("- files: " + ", ".join(res["file_names"]))
        else:
            L.append("- styles: " + ", ".join("%s **%s**" % (s["role"], s["id"]) + (" (via '%s')" % s["matched"]) for s in res["styles"]))
            L.append("- files: " + ", ".join(res["file_names"]))
        if res["modifiers"]:
            L.append("- modifiers:")
            for m in res["modifiers"]:
                L.append("    - **%s** (\"%s\"): %s" % (m["id"], m["phrase"], m["effect"]))
        if res.get("blend_plan"):
            L.append("- blend plan:")
            for b in res["blend_plan"]:
                L.append("    " + ("" if b.startswith("  ") else "- ") + b.strip() if not b.startswith("  ") else "        " + b.strip())
        L.append("- after drawing run: `%s`" % res["validate_cmd"])
        if with_brief:
            ids = res["multi_styles"] if res["mode"] == "multi" else [s["id"] for s in res["styles"]]
            for sid in ids:
                L.append("")
                L.append(self.brief(sid))
        return "\n".join(L)

    # ------------------------------------------------------------------
    def lint(self):
        errs, warns = [], []
        reg = self.reg
        alias_owner = {}
        for sid, s in reg.items():
            for f in REQUIRED_FIELDS:
                if f not in s or s[f] in (None, "", [], {}):
                    errs.append("%s: missing/empty field %r" % (sid, f))
            if s.get("id") and s["id"] != slug(s["id"]):
                errs.append("%s: id must be a lowercase slug" % sid)
            pal = s.get("palette", {})
            if not isinstance(pal, dict) or "guidance" not in pal:
                errs.append("%s: palette must be an object with 'guidance' (and optional 'swatches')" % sid)
            else:
                for sw in pal.get("swatches", []):
                    if not re.fullmatch(r"#[0-9a-fA-F]{6}", sw):
                        errs.append("%s: swatch %r is not #rrggbb" % (sid, sw))
            for rel in ("compatible_with", "conflicts_with", "extends"):
                vals = s.get(rel, [])
                vals = [vals] if isinstance(vals, str) else vals
                for v in vals:
                    if v not in reg:
                        errs.append("%s: %s references unknown style %r" % (sid, rel, v))
                    if v == sid:
                        errs.append("%s: %s references itself" % (sid, rel))
            both = set(s.get("compatible_with", [])) & set(s.get("conflicts_with", []))
            if both:
                errs.append("%s: styles both compatible and conflicting: %s" % (sid, ", ".join(sorted(both))))
            ref = s.get("reference", "")
            fname, _, anchor = ref.partition("#")
            path = REFERENCE_DIR / fname
            if not path.exists():
                errs.append("%s: reference file %s does not exist" % (sid, fname))
            elif anchor:
                text = path.read_text(encoding="utf-8")
                if not re.search(r"^#{1,4}\s.*\{#%s\}\s*$" % re.escape(anchor), text, re.M):
                    errs.append("%s: anchor {#%s} not found in %s" % (sid, anchor, fname))
            for ph in [s.get("name", "")] + s.get("aliases", []):
                n = norm(ph)
                alias_owner.setdefault(n, sid)  # shared aliases are intentional: they route to both styles (a blend)
            if not all(isinstance(w, str) for w in s.get("weak_aliases", [])):
                errs.append("%s: weak_aliases must be a list of strings" % sid)
            for k in s.get("checks", {}):
                if k not in KNOWN_CHECKS:
                    errs.append("%s: unknown check %r (see validate_svg.py run_style_checks)" % (sid, k))
            if len(s.get("aliases", [])) < 2:
                warns.append("%s: fewer than 2 aliases; routing may miss natural phrasings" % sid)
        for sid, s in reg.items():
            for o in s.get("compatible_with", []):
                if o in reg and sid in reg[o].get("conflicts_with", []):
                    errs.append("%s says compatible with %s, but %s says it conflicts" % (sid, o, o))
            for o in s.get("conflicts_with", []):
                if o in reg and sid in reg[o].get("compatible_with", []):
                    errs.append("%s says it conflicts with %s, but %s says compatible" % (sid, o, o))
        for m in self.mods:
            if not m.get("triggers") or not m.get("effect"):
                errs.append("modifier %s: needs triggers and effect" % m.get("id"))
        return errs, warns


KNOWN_CHECKS = {
    "forbid_elements", "require_elements_any", "max_colors", "min_colors", "forbid_path_curves", "integer_coords",
    "require_shape_rendering", "max_filters", "min_filters", "max_gradients", "min_gradients", "min_elements",
    "max_elements", "min_groups", "require_text", "forbid_text", "min_stroke_widths", "max_stroke_widths",
    "require_stroke", "forbid_stroke", "require_linecap", "require_linejoin", "dark_base", "light_base", "allow_bleed",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-brief", action="store_true", help="resolution only, without the style briefs")
    ap.add_argument("--menu", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show", metavar="ID", nargs="+")
    ap.add_argument("--compat", nargs="+", metavar="ID")
    ap.add_argument("--lint", action="store_true")
    a = ap.parse_args()
    r = Router()
    if a.lint:
        errs, warns = r.lint()
        for w in warns:
            print("warn ", w)
        for e in errs:
            print("ERROR", e)
        print("%d styles, %d modifiers, %d errors, %d warnings" % (len(r.reg), len(r.mods), len(errs), len(warns)))
        sys.exit(1 if errs else 0)
    if a.menu:
        print(r.menu())
        return
    if a.list:
        for sid, s in r.reg.items():
            print("%-22s %-28s %s" % (sid, s["name"], ", ".join(s.get("aliases", []))))
        return
    if a.show:
        for sid in a.show:
            if sid not in r.reg:
                sys.exit("unknown style %r (try --list)" % sid)
            print(r.brief(sid))
            print()
        return
    if a.compat:
        for sid in a.compat:
            if sid not in r.reg:
                sys.exit("unknown style %r" % sid)
        print("\n".join(r.blend_plan(a.compat)))
        return
    if not a.prompt:
        ap.print_help()
        return
    res = r.resolve(a.prompt)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(r.format_resolution(res, not a.no_brief))


if __name__ == "__main__":
    main()
