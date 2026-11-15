"""Build Sunday Serif from sources/ into fonts/.

usage: python scripts/build.py [--only-variable]

  fonts/variable/  SundaySerif[BURN,INKB,WORN,wght].ttf, SundaySerif-Italic[...].ttf
  fonts/webfonts/  WOFF2 for the web, all at 1000 UPM:
                   SundaySerifText-*.woff2  weight axis only, effects at 0 (~55 KB): body text
                   SundaySerif-*.woff2      all four axes (~1.3 MB): load only where effects show
                   SundaySerifGrain-*.woff2  Sunday Serif Grain, the Grain Blur axis (~1 MB)
  fonts/ttf/, fonts/otf/  static Regular, Medium, SemiBold and italics (effects at 0)

Sunday Serif Grain (SundaySerifGrain[GRAN].ttf and its italic in fonts/variable/) is a separate
display cut with one axis, Grain Blur. Its masters come from scripts/grain_blur.py.

The version comes from the VERSION file: SemVer X.Y.Z becomes font version X.YYZ
(v0.1.0 -> 0.010, v0.12.3 -> 0.123, v1.0.0 -> 1.000).
"""
import argparse
import copy
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools import subset
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables import ttProgram
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
BUILD = ROOT / "build"
FONTS = ROOT / "fonts"
FAMILY = "Sunday Serif"
PS_FAMILY = "SundaySerif"
AXES = "[BURN,INKB,WORN,wght]"
WEIGHTS = [(400, "Regular"), (500, "Medium"), (600, "SemiBold")]
STYLES = [  # (designspace, italic)
    ("SundaySerif.designspace", False),
    ("SundaySerif-Italic.designspace", True),
]
GRAIN_FAMILY = "Sunday Serif Grain"
GRAIN_PS = "SundaySerifGrain"
GRAIN_STYLES = [
    ("SundaySerifGrain.designspace", False),
    ("SundaySerifGrain-Italic.designspace", True),
]


def version():
    raw = (ROOT / "VERSION").read_text().strip()
    major, minor, patch = (int(p) for p in raw.split("-")[0].split("."))
    if minor > 99 or patch > 9:
        sys.exit(f"VERSION {raw}: minor must be <= 99 and patch <= 9 to map onto font version X.YYZ")
    return raw, major + (minor * 10 + patch) / 1000


def set_version(font, raw, rev, psname):
    font["head"].fontRevision = rev
    name = font["name"]
    name.setName(f"Version {rev:.3f}", 5, 3, 1, 0x409)
    name.setName(f"{rev:.3f};KKRT;{psname}", 3, 3, 1, 0x409)


def smart_dropout(font):
    prep = ttProgram.Program()
    prep.fromAssembly(["PUSHW[ ]", "511", "SCANCTRL[ ]", "PUSHB[ ]", "4", "SCANTYPE[ ]"])
    font["prep"] = newTable("prep")
    font["prep"].program = prep
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000F}
    font["gasp"] = gasp


def stat(font, italic):
    axes = [
        dict(tag="wght", name="Weight", values=[
            dict(value=400, name="Regular", flags=2, linkedValue=700),
            dict(value=500, name="Medium"),
            dict(value=600, name="SemiBold"),
        ]),
        # Effect axes name only their default: with more entries Windows builds style
        # names longer than 32 characters (there are no named instances for them anyway).
        dict(tag="BURN", name="Light Burn", values=[dict(value=0, name="Normal", flags=2)]),
        dict(tag="INKB", name="Ink Bleed", values=[dict(value=0, name="Normal", flags=2)]),
        dict(tag="WORN", name="Worn Print", values=[dict(value=0, name="Normal", flags=2)]),
        dict(tag="ital", name="Italic", values=[dict(value=1, name="Italic")] if italic
             else [dict(value=0, name="Roman", flags=2, linkedValue=1)]),
    ]
    buildStatTable(font, axes, elidedFallbackName=2)


def grain_stat(font, italic):
    axes = [
        dict(tag="GRAN", name="Grain Blur", values=[dict(value=0, name="Normal", flags=2)]),
        dict(tag="ital", name="Italic", values=[dict(value=1, name="Italic")] if italic
             else [dict(value=0, name="Roman", flags=2, linkedValue=1)]),
    ]
    buildStatTable(font, axes, elidedFallbackName=2)


def build_grain(ds, italic, raw, rev):
    """Sunday Serif Grain: one Grain Blur axis, Regular and Italic."""
    BUILD.mkdir(exist_ok=True)
    raw_path = BUILD / ds.replace(".designspace", ".ttf")
    subprocess.run([sys.executable, "-m", "fontmake", "-m", str(SOURCES / ds), "-o", "variable",
                    "--flatten-components", "--output-path", str(raw_path)], check=True)
    font = TTFont(raw_path)
    stem = GRAIN_PS + ("-Italic" if italic else "")
    font["name"].setName(GRAIN_PS + ("Italic" if italic else ""), 25, 3, 1, 0x409)
    set_version(font, raw, rev, stem if italic else f"{GRAIN_PS}-Regular")
    grain_stat(font, italic)
    smart_dropout(font)
    font["name"].removeNames(platformID=1)
    out = FONTS / "variable" / f"{stem}[GRAN].ttf"
    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(out)
    return out


def build_variable(ds, italic, raw, rev):
    BUILD.mkdir(exist_ok=True)
    raw_path = BUILD / ds.replace(".designspace", ".ttf")
    subprocess.run([sys.executable, "-m", "fontmake", "-m", str(SOURCES / ds), "-o", "variable",
                    "--flatten-components", "--output-path", str(raw_path)], check=True)
    font = TTFont(raw_path)
    stem = PS_FAMILY + ("-Italic" if italic else "")
    name = font["name"]
    name.setName(PS_FAMILY + ("Italic" if italic else ""), 25, 3, 1, 0x409)
    set_version(font, raw, rev, f"{stem}" if italic else f"{PS_FAMILY}-Regular")
    stat(font, italic)
    smart_dropout(font)
    name.removeNames(platformID=1)
    out = FONTS / "variable" / f"{stem}{AXES}.ttf"
    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(out)
    return out


def reload(font):
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    return TTFont(buf, lazy=False)


def strip_pores(font):
    """Drop contours that stay a single point in every master (the Worn Print pores once WORN is pinned)."""
    glyf, gvar = font["glyf"], font.get("gvar")
    for gname in font.getGlyphOrder():
        glyph = glyf[gname]
        if glyph.numberOfContours <= 0:
            continue
        coords, ends, flags = glyph.getCoordinates(glyf)
        variations = gvar.variations.get(gname, []) if gvar else []
        for tv in variations:  # the instancer leaves IUP gaps: fill them so pores are recognised
            if None in tv.coordinates:
                tv.calcInferredDeltas(list(coords) + [(0, 0)] * 4, list(ends))
                tv.coordinates = [(round(x), round(y)) for x, y in tv.coordinates]
        keep, start = [], 0
        for end in ends:
            pts = list(range(start, end + 1))
            start = end + 1
            dead = len({tuple(coords[i]) for i in pts}) == 1 and all(
                None not in (d := [tv.coordinates[i] for i in pts]) and len(set(d)) == 1 for tv in variations)
            keep.append((pts, not dead))
        if all(k for _, k in keep):
            continue
        idx = [i for pts, k in keep if k for i in pts]
        ends2, n = [], 0
        for pts, k in keep:
            if k:
                n += len(pts)
                ends2.append(n - 1)
        glyph.coordinates = GlyphCoordinates([coords[i] for i in idx])
        glyph.flags = bytearray(flags[i] for i in idx)
        glyph.endPtsOfContours = ends2
        glyph.numberOfContours = len(ends2)
        for tv in variations:  # the last four points are the phantom points
            tv.coordinates = [tv.coordinates[i] for i in idx] + tv.coordinates[len(coords):]


def drop_flat_points(font, tol=1.5):
    """Drop the points the effect masters need but a pinned font does not: quads the densify
    step split in two, off-curves that sit on the straight line between two on-curves,
    on-curves on a straight line, and on-curves halfway between two off-curves.
    A point goes only if that holds in every remaining master."""
    glyf, gvar = font["glyf"], font.get("gvar")
    for gname in font.getGlyphOrder():
        glyph = glyf[gname]
        if glyph.numberOfContours <= 0:
            continue
        coords, ends, flags = glyph.getCoordinates(glyf)
        coords = [tuple(c) for c in coords]
        n = len(coords)
        tvs = gvar.variations.get(gname, []) if gvar else []
        full = coords + [(0, 0)] * 4  # phantom points (unused by the tests)
        for tv in tvs:
            if None in tv.coordinates:
                tv.calcInferredDeltas(full, list(ends))
                tv.coordinates = [(round(x), round(y)) for x, y in tv.coordinates]
        masters = [list(coords)] + [[(x + d[0], y + d[1]) for (x, y), d in zip(coords, tv.coordinates[:n])] for tv in tvs]
        on = [bool(f & 1) for f in flags]

        def flat(a, b, c):  # b lies on segment a-c in every master
            for m in masters:
                (ax, ay), (bx, by), (cx, cy) = m[a], m[b], m[c]
                dx, dy = cx - ax, cy - ay
                L = (dx * dx + dy * dy) ** 0.5
                if L < 1e-6 or abs((bx - ax) * dy - (by - ay) * dx) / L > tol:
                    return False
                t = ((bx - ax) * dx + (by - ay) * dy) / (L * L)
                if not -0.01 <= t <= 1.01:
                    return False
            return True

        def mid(a, b, c):
            return all(abs((m[a][0] + m[c][0]) / 2 - m[b][0]) <= tol and abs((m[a][1] + m[c][1]) / 2 - m[b][1]) <= tol for m in masters)

        keep = [True] * n
        start = 0
        for end in ends:
            idx = list(range(start, end + 1))
            start = end + 1
            for rule in ("merge", "offline", "online", "implied"):
                changed = True
                while changed:
                    changed = False
                    live = [i for i in idx if keep[i]]
                    if len(live) <= 3:
                        break
                    for j, i in enumerate(live):
                        p, q = live[j - 1], live[(j + 1) % len(live)]
                        if rule == "offline" and not on[i] and on[p] and on[q] and flat(p, i, q):
                            keep[i] = False; changed = True; break
                        if rule == "online" and on[i] and on[p] and on[q] and flat(p, i, q):
                            keep[i] = False; changed = True; break
                        if rule == "merge" and len(live) > 5 and on[i] and not on[p] and not on[q]:
                            a, b = live[j - 2], live[(j + 2) % len(live)]
                            # a quad split in two by the densify step: put the original quad back
                            if on[a] and on[b] and mid(p, i, q) and all(
                                    abs((2 * m[p][0] - m[a][0]) - (2 * m[q][0] - m[b][0])) <= 4 * tol and
                                    abs((2 * m[p][1] - m[a][1]) - (2 * m[q][1] - m[b][1])) <= 4 * tol for m in masters):
                                for m in masters:
                                    m[p] = (2 * m[p][0] - m[a][0], 2 * m[p][1] - m[a][1])
                                keep[i] = keep[q] = False; changed = True; break
                        if rule == "implied" and on[i] and not on[p] and not on[q] and mid(p, i, q):
                            keep[i] = False; changed = True; break
        if all(keep):
            for tv in tvs:
                tv.optimize(full, list(ends))
            continue
        idx = [i for i in range(n) if keep[i]]
        ends2, k, start = [], 0, 0
        for end in ends:
            k += sum(keep[start:end + 1]); start = end + 1
            ends2.append(k - 1)
        coords = masters[0]
        for tv, m in zip(tvs, masters[1:]):
            tv.coordinates = [(round(mx - x), round(my - y)) for (x, y), (mx, my) in zip(coords, m)] + list(tv.coordinates[n:])
        glyph.coordinates = GlyphCoordinates([coords[i] for i in idx])
        glyph.flags = bytearray(flags[i] for i in idx)
        glyph.endPtsOfContours = ends2
        glyph.numberOfContours = len(ends2)
        new = [coords[i] for i in idx]
        for tv in tvs:
            tv.coordinates = [(round(tv.coordinates[i][0]), round(tv.coordinates[i][1])) for i in idx] + list(tv.coordinates[n:])
            tv.optimize(new + [(0, 0)] * 4, ends2)


def scale_upem_keep_iup(font, upem):
    """scale_upem with gvar deltas made explicit first, then IUP-optimised again at the new size.

    Scaling optimised deltas rounds the default outline, so reference points that were a few
    units apart can land on the same coordinate and IUP infers the skipped points differently:
    at high Light Burn that drew thin cuts through the letters. Optimising after the scale keeps
    every inferred delta consistent with the rounded outline."""
    glyf, gvar = font["glyf"], font.get("gvar")

    def outline(gname):
        glyph = glyf[gname]
        if glyph.numberOfContours <= 0:
            return None, None
        coords, ends, _ = glyph.getCoordinates(glyf)
        return list(coords) + [(0, 0)] * 4, list(ends)

    if gvar:
        for gname, tvs in gvar.variations.items():
            coords, ends = outline(gname)
            if coords is None:
                continue
            for tv in tvs:
                if None in tv.coordinates:
                    tv.calcInferredDeltas(coords, ends)
    scale_upem(font, upem)
    if gvar:
        for gname, tvs in gvar.variations.items():
            coords, ends = outline(gname)
            if coords is None:
                continue
            for tv in tvs:
                tv.optimize(coords, ends)


def woff2(src, dst, pin=None):
    """WOFF2 at 1000 UPM (about 15% smaller, no visible change at text sizes); `pin` fixes axes."""
    font = TTFont(src, lazy=False)
    if pin:
        font = reload(instancer.instantiateVariableFont(font, pin))
        strip_pores(font)
        drop_flat_points(font)
    font = reload(font)
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=font.getBestCmap().keys())
    sub.subset(font)  # drops glyphs nothing can reach any more
    scale_upem_keep_iup(font, 1000)
    font.flavor = "woff2"
    dst.parent.mkdir(parents=True, exist_ok=True)
    font.save(dst)


def clean_path(glyphset, name):
    rec = DecomposingRecordingPen(glyphset)
    glyphset[name].draw(rec)
    path = pathops.Path()
    rec.replay(path.getPen())
    return pathops.simplify(path, fix_winding=True, keep_starting_points=True, clockwise=False)


def build_statics(vf_path, italic, raw, rev):
    out = []
    for wght, wname in WEIGHTS:
        font = instancer.instantiateVariableFont(
            TTFont(vf_path), {"wght": wght, "BURN": 0, "INKB": 0, "WORN": 0}, updateFontNames=False)
        drop_flat_points(font)
        style = (wname if not italic else ("Italic" if wname == "Regular" else f"{wname} Italic"))
        psname = f"{PS_FAMILY}-{style.replace(' ', '')}"
        ribbi = wname == "Regular"
        fam = FAMILY if ribbi else f"{FAMILY} {wname}"
        name = font["name"]
        for nid in (1, 2, 3, 4, 6, 16, 17, 25):
            name.removeNames(nameID=nid)
        name.setName(fam, 1, 3, 1, 0x409)
        name.setName("Italic" if italic else "Regular", 2, 3, 1, 0x409)
        name.setName(f"{FAMILY} {style}", 4, 3, 1, 0x409)
        name.setName(psname, 6, 3, 1, 0x409)
        if not ribbi:
            name.setName(FAMILY, 16, 3, 1, 0x409)
            name.setName(style, 17, 3, 1, 0x409)
        set_version(font, raw, rev, psname)
        name.removeNames(platformID=1)
        os2 = font["OS/2"]
        os2.usWeightClass = wght
        sel = os2.fsSelection & ~(1 | 32 | 64)
        os2.fsSelection = sel | (1 if italic else 0) | (64 if not italic else 0)
        font["head"].macStyle = 2 if italic else 0
        order = font.getGlyphOrder()
        glyphset = font.getGlyphSet()
        paths = {g: clean_path(glyphset, g) for g in order}
        adv = {g: font["hmtx"][g][0] for g in order}

        tt = copy.deepcopy(font)
        glyf = tt["glyf"]
        for g in order:
            pen = TTGlyphPen(None)
            paths[g].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
            glyf[g] = pen.glyph()
        for g in order:
            gg = glyf[g]
            gg.recalcBounds(glyf)
            tt["hmtx"][g] = (adv[g], gg.xMin if gg.numberOfContours else 0)
        ttf = FONTS / "ttf" / f"{psname}.ttf"
        ttf.parent.mkdir(parents=True, exist_ok=True)
        tt.save(ttf)

        ot = TTFont(ttf)
        charstrings = {}
        for g in order:
            pen = T2CharStringPen(adv[g], None)
            paths[g].draw(pen)
            charstrings[g] = pen.getCharString()
        for t in ("glyf", "loca", "gasp", "prep", "fpgm", "cvt "):
            if t in ot:
                del ot[t]
        fb = FontBuilder(font=ot)
        fb.isTTF = False
        fb.setupCFF(psname, {"FullName": f"{FAMILY} {style}", "FamilyName": fam}, charstrings, {})
        ot["maxp"] = newTable("maxp")
        ot["maxp"].tableVersion = 0x00005000
        ot["maxp"].numGlyphs = len(order)
        ot["post"].formatType = 3.0
        ot.sfntVersion = "OTTO"
        otf = FONTS / "otf" / f"{psname}.otf"
        otf.parent.mkdir(parents=True, exist_ok=True)
        ot.save(otf)
        out.append(ttf)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-variable", action="store_true", help="skip the statics (faster)")
    args = ap.parse_args()
    raw, rev = version()
    print(f"Sunday Serif {raw} (font version {rev:.3f})")
    for sub in ("variable", "webfonts", "ttf", "otf", "blur"):
        shutil.rmtree(FONTS / sub, ignore_errors=True)
    web = FONTS / "webfonts"
    for ds, italic in STYLES:
        vf = build_variable(ds, italic, raw, rev)
        suffix = "-Italic" if italic else ""
        woff2(vf, web / f"{PS_FAMILY}{suffix}-Variable.woff2")
        woff2(vf, web / f"{PS_FAMILY}Text{suffix}-Variable.woff2", pin={"BURN": 0, "INKB": 0, "WORN": 0})
        if args.only_variable:
            continue
        build_statics(vf, italic, raw, rev)
    for ds, italic in GRAIN_STYLES:
        vf = build_grain(ds, italic, raw, rev)
        woff2(vf, web / f"{GRAIN_PS}{'-Italic' if italic else ''}-Variable.woff2")
    print("done:", ", ".join(sorted(str(p.relative_to(ROOT)) for p in FONTS.rglob("*.*"))))


if __name__ == "__main__":
    main()
