"""Point-compatible weight derivation from a Sunday Serif master UFO.

Every contour is offset along its normal (stems by dS, horizontals by dH) and the glyph is
re-centred and widened by D, so the result interpolates with the master it comes from.
"""
import math

import numpy as np

# Total extra stem, extra horizontal thickness, extra width, in units of 4096 UPM.
# Only Bold has masters: its stem is about 1.7 times Regular's (353 -> 600 on the l), so it
# reads as a real bold next to SemiBold. Medium and SemiBold are placed on the weight axis by
# the designspace axis map, so the stems grow by the same ratio at every step.
W = {"Bold": (300, 34, 50)}
ITALIC_ANGLE = 16
MARK_WEIGHT = 0.5
# Pictograms keep the same shape and width in every weight: the Sunday flower (U+273F).
SAME_IN_ALL_WEIGHTS = {"uni273F"}


def embolden(glyph, dx, dy, s, cx, t, base=None):
    for ci, c in enumerate(glyph.contours):
        if base is not None and ci >= base:
            # Worn Print pores and grain keep their size: they only follow the glyph.
            ox, oy = 0.0, 0.0
        else:
            ox, oy = dx, dy
        p = np.array([(q.x - q.y * t, q.y) for q in c.points], float)
        if len(p) < 3:
            continue
        tan = np.roll(p, -1, 0) - np.roll(p, 1, 0)
        nr = np.stack([tan[:, 1], -tan[:, 0]], 1)
        nr /= np.linalg.norm(nr, axis=1)[:, None] + 1e-9
        for i, q in enumerate(c.points):
            u = cx + (p[i, 0] - cx) * s - nr[i, 0] * ox
            y = p[i, 1] - nr[i, 1] * oy
            q.x = float(u + y * t)
            q.y = float(y)


def derive(font, weight, italic, stem, base_counts=None):
    """Make `font` (a Regular master) into `weight` in place. `stem` is the Regular stem width.

    `base_counts` maps glyph names to their number of drawn contours; any contour after those
    (the Worn Print pores and grain) is moved with the glyph but not offset.
    """
    t = math.tan(math.radians(ITALIC_ANGLE)) if italic else 0.0
    d_stem, d_horiz, d_width = W[weight]
    dx, dy = d_stem / 2, d_horiz / 2
    k = 2048 / (2048 + 2 * dy)  # keeps the x-height where it was
    shift, widths = {}, {g.name: g.width for g in font}
    for g in font:
        if not g.contours or g.name in SAME_IN_ALL_WEIGHTS:
            continue
        b = g.getBounds(font)
        if not b:
            continue
        ink = b[2] - b[0]
        cx = (b[0] + b[2]) / 2
        if g.width == 0:
            # Marks are thin and narrow: the full offset and the horizontal squeeze crush the
            # caron's notch. They get half the weight and keep their width.
            s, mx, my = 1.0, dx * MARK_WEIGHT, dy * MARK_WEIGHT
        else:
            s = float(np.clip((ink + d_width - d_stem) / ink, 0.85, 1.1)) if ink > stem * 1.5 else 1.0
            mx, my = dx, dy
        embolden(g, mx, my, s, cx - ((b[1] + b[3]) / 2) * t, t,
                 base_counts.get(g.name) if base_counts else None)
        for c in g.contours:
            for q in c.points:
                y = float(q.y * k + dy * k)
                q.x = float(q.x + (y - q.y) * t)
                q.y = y
        if g.width == 0 or g.components:
            continue  # marks stay centred; mixed glyphs keep their width
        nb = g.getBounds(font)
        delta = (nb[2] - nb[0]) - ink
        for c in g.contours:
            for q in c.points:
                q.x = float(q.x + delta / 2)
        g.width = round(g.width + delta)
        shift[g.name] = delta

    def depth(name):
        g = font[name]
        return 0 if not g.components else 1 + max(depth(c.baseGlyph) for c in g.components)

    for g in sorted((g for g in font if g.components), key=lambda g: depth(g.name)):
        run, last, first = 0.0, 0.0, None
        for c in g.components:
            tr = c.transformation
            if widths.get(c.baseGlyph, 0) == 0:
                c.transformation = (tr[0], tr[1], tr[2], tr[3], float(tr[4] + last), tr[5])
            else:
                d = shift.get(c.baseGlyph, 0) * tr[0]
                c.transformation = (tr[0], tr[1], tr[2], tr[3], float(tr[4] + run), tr[5])
                if first is None:
                    first = d
                last = run + d / 2
                run += d
        if g.contours and first:
            for cc in g.contours:
                for q in cc.points:
                    q.x = float(q.x + first / 2)
        if g.width:
            g.width = round(g.width + run)
            shift[g.name] = run
