"""Sunday Serif Blur: a static COLRv0 colour font made from a static TTF.

Each glyph becomes a core in the text colour (palette index 0xFFFF) over eight
halo layers, offset outwards with decreasing alpha.

usage: blur.py SRC.ttf DST.ttf FAMILY PSFAMILY STYLE
"""
import sys

import numpy as np
from fontTools.colorLib.builder import buildCOLR, buildCPAL
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates

SPREAD = [270, 215, 165, 120, 80, 45, 15, -12]
ALPHA = [0.07, 0.08, 0.09, 0.10, 0.12, 0.14, 0.18, 0.25]
CORE = -35  # the core sits slightly inside the outline, so the halo shows at its edge


def offset(glyph, glyf, d):
    coords, ends, flags = glyph.getCoordinates(glyf)
    points = np.array(coords, float)
    start, out = 0, []
    for end in ends:
        c, fl = points[start:end + 1], flags[start:end + 1]
        start = end + 1
        if len(c) < 3:
            continue
        t = np.roll(c, -1, 0) - np.roll(c, 1, 0)
        n = np.stack([t[:, 1], -t[:, 0]], 1)
        n /= np.linalg.norm(n, axis=1)[:, None] + 1e-9
        out.append((c - n * d, fl))  # TrueType outer contours are clockwise
    return out


def layer_glyph(contours):
    g = Glyph()
    g.numberOfContours = len(contours)
    allc = np.concatenate([q for q, _ in contours])
    g.coordinates = GlyphCoordinates([tuple(map(float, p)) for p in np.round(allc)])
    g.flags = bytearray([fl for _, f in contours for fl in f])
    g.endPtsOfContours = list(np.cumsum([len(q) for q, _ in contours]) - 1)
    g.program = ttProgram.Program()
    g.program.fromBytecode(b"")
    return g


def main():
    src, dst, family, psfamily, style = sys.argv[1:6]
    font = TTFont(src)
    glyf, hmtx = font["glyf"], font["hmtx"]
    order = font.getGlyphOrder()
    new, layers = {}, {}
    for name in order:
        g = glyf[name]
        if g.numberOfContours <= 0:
            continue
        stack = []
        for i, d in enumerate(SPREAD):
            new[f"{name}.blur{i}"] = layer_glyph(offset(g, glyf, d))
            stack.append((f"{name}.blur{i}", i))
        new[f"{name}.core"] = layer_glyph(offset(g, glyf, CORE))
        stack.append((f"{name}.core", 0xFFFF))
        layers[name] = stack
    font.setGlyphOrder(order + list(new))
    for name, g in new.items():
        glyf[name] = g
        g.recalcBounds(glyf)
        hmtx[name] = (0, g.xMin if g.numberOfContours else 0)
    font["maxp"].numGlyphs = len(order) + len(new)
    font["post"].formatType = 3.0
    font["CPAL"] = buildCPAL([[(0, 0, 0, a) for a in ALPHA] + [(0, 0, 0, 1.0)]])
    font["COLR"] = buildCOLR(layers, version=0)
    name = font["name"]
    for nid in (1, 2, 3, 4, 6, 16, 17, 25):
        name.removeNames(nameID=nid)
    name.setName(family, 1, 3, 1, 0x409)
    name.setName(style, 2, 3, 1, 0x409)
    name.setName(f"{family} {style}", 4, 3, 1, 0x409)
    name.setName(f"{psfamily}-{style}", 6, 3, 1, 0x409)
    font.save(dst)
    print(f"{dst}: {len(new)} layer glyphs")


if __name__ == "__main__":
    main()
