"""Rebuild the Ink Bleed and Worn Print masters from the plain Light Burn masters.

usage: python scripts/effects.py [--only NAME]   (e.g. --only Regular-B0)

For every weight of both styles, the masters at Light Burn -100, 0 and +100 get two
effect copies, written over sources/{Roman,Italic}/SundaySerif-*-B*-{Ink100,Worn100}.ufo:

  Ink100   every contour spreads outwards by about a third of the stem, with a slow
           blotchy wobble along the edge, extra ink pooling in the inner corners
           (counters and joins fill up) and tighter spacing to match.
  Worn100  the edges are eaten away unevenly with chipped bites, never more than 30%
           of the local stroke, and the pores (the collapsed 8-point contours at the
           end of each glyph) open into scratches along the stroke and small specks.

The plain masters are never touched, so every master stays point-compatible: points
only move, contours are never added or removed. Seeds are fixed per glyph name, so the
output is reproducible and the texture is the same across weights and Light Burn.
"""
import argparse
import math
import random
import zlib
from pathlib import Path

import numpy as np
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.pens.pointInsidePen import PointInsidePen

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
DESIGNSPACES = ["SundaySerif.designspace", "SundaySerif-Italic.designspace"]

# All sizes are fractions of the stem of "l" in the weight's Light Burn 0 master.
INK_SPREAD = 0.36      # mean outward spread
INK_WOBBLE = 0.6       # how much the spread varies along the edge (x INK_SPREAD)
INK_POOL = 0.55        # extra spread in inner corners
INK_TRACK = 0.7        # spacing taken back (x INK_SPREAD)
WEAR = 0.15            # mean edge erosion
WEAR_WOBBLE = 0.9
CHIPS = 0.14           # chipped bites per quarter stem of outline
CHIP_DEPTH = 0.45
WEAR_KEEP = 0.3        # erosion never takes more than this share of the local stroke
SCRATCHES = 0.65       # share of pores that become scratches (the rest are specks)


def is_dot(c):
    return len({(p.x, p.y) for p in c.points}) == 1


def outline_count(G):
    """Number of real contours: the pores are the collapsed 8-point contours at the end."""
    k = len(G.contours)
    while k and len(G.contours[k - 1].points) == 8 and is_dot(G.contours[k - 1]):
        k -= 1
    return k


def arr(c):
    return np.array([(p.x, p.y) for p in c.points], float)


def geom(A):
    """Outward normal (away from the ink), arc position, length and turn (>0 = inner corner)."""
    t = np.roll(A, -1, 0) - np.roll(A, 1, 0)
    t /= np.linalg.norm(t, axis=1)[:, None] + 1e-9
    out = np.stack([-t[:, 1], t[:, 0]], 1)
    seg = np.linalg.norm(np.roll(A, -1, 0) - A, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)[:-1]])
    a = A - np.roll(A, 1, 0)
    b = np.roll(A, -1, 0) - A
    turn = np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1))
    return out, s, seg.sum(), turn


def noise(s, L, stem, rng, waves):
    """Smooth periodic noise along a contour; wavelengths in stems."""
    v = np.zeros_like(s)
    for wl, amp in waves:
        k = max(1, round(L / (wl * stem)))
        v += amp * np.sin(2 * math.pi * k * s / max(L, 1) + rng.uniform(0, 2 * math.pi))
    return v


def smooth(v, s, L, width):
    out = np.zeros_like(v)
    for i in range(len(v)):
        d = np.abs(s - s[i])
        d = np.minimum(d, L - d)
        w = np.exp(-((d / width) ** 2))
        out[i] = (w * v).sum() / w.sum()
    return out


def area(Q):
    return 0.5 * np.sum(Q[:, 0] * np.roll(Q[:, 1], -1) - np.roll(Q[:, 0], -1) * Q[:, 1])


def crossings(A, i):
    p = A[i]
    r = A[(i + 1) % len(A)] - p
    S = np.roll(A, -1, 0) - A
    rxs = r[0] * S[:, 1] - r[1] * S[:, 0]
    qp = A - p
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (qp[:, 0] * S[:, 1] - qp[:, 1] * S[:, 0]) / rxs
        u = (qp[:, 0] * r[1] - qp[:, 1] * r[0]) / rxs
    ok = (np.abs(rxs) > 1e-9) & (t > 1e-6) & (t < 1 - 1e-6) & (u > 1e-6) & (u < 1 - 1e-6)
    return [(j, p + t[j] * r) for j in np.where(ok)[0]]


def untangle(c, stem, maxfrac=0.34):
    """Collapse the small reversed loops that offsetting leaves in tight corners onto their
    crossing point: under the non-zero rule they would show as specks or spikes. Big loops
    are real shapes (a notch closing into a counter, like the foot of n) and stay."""
    A = arr(c)
    n = len(A)
    if n < 6:
        return
    sign = np.sign(area(A))
    for _ in range(4):
        changed = False
        for i in range(n):
            for j, X in crossings(A, i):
                a, b = (i, j) if (j - i) % n <= (i - j) % n else (j, i)
                span = (b - a) % n
                if span < 2 or span > maxfrac * n:
                    continue
                loop = np.array([X] + [A[(a + m) % n] for m in range(1, span + 1)])
                if np.sign(area(loop)) == sign or abs(area(loop)) > (0.45 * stem) ** 2:
                    continue
                for m in range(1, span + 1):
                    A[(a + m) % n] = X
                changed = True
        if not changed:
            break
    for p, (x, y) in zip(c.points, A):
        p.x, p.y = float(x), float(y)


def glyph_rng(name, seed):
    return random.Random(zlib.crc32(name.encode()) * 31 + seed)


def ink_glyph(G, k, stem):
    rng = glyph_rng(G.name, 7)
    for c in G.contours[:k]:
        if len(c.points) < 3:
            continue
        A = arr(c)
        N, s, L, turn = geom(A)
        wob = noise(s, L, stem, rng, [(2.2, 0.55), (0.9, 0.35), (0.45, 0.25)])
        pool = smooth(np.clip(turn, 0, None), s, L, 0.25 * stem)
        d = np.maximum(stem * (INK_SPREAD * (1 + INK_WOBBLE * wob) + INK_POOL * pool), 0.05 * stem)
        for i, p in enumerate(c.points):
            p.x = float(p.x + N[i, 0] * d[i])
            p.y = float(p.y + N[i, 1] * d[i])
        untangle(c, stem)


def ink(F, stem):
    track = INK_TRACK * INK_SPREAD * stem
    shift = {}
    widths = {G.name: G.width for G in F}
    for G in F:
        if not G.contours:
            continue
        ink_glyph(G, outline_count(G), stem)
        if G.width and not G.components:
            for c in G.contours:
                for p in c.points:
                    p.x = float(p.x - track / 2)
            G.width = max(200, round(G.width - track))
            shift[G.name] = -track

    # Composites follow their components: every spacing component shifts the ones after it.
    def depth(n):
        g = F[n]
        return 0 if not g.components else 1 + max(depth(c.baseGlyph) for c in g.components)

    for G in sorted([G for G in F if G.components], key=lambda G: depth(G.name)):
        R = last = 0.0
        first = None
        for c in G.components:
            t = c.transformation
            if widths.get(c.baseGlyph, 0) == 0:
                c.transformation = (t[0], t[1], t[2], t[3], float(t[4] + last), t[5])
            else:
                d = shift.get(c.baseGlyph, 0) * t[0]
                c.transformation = (t[0], t[1], t[2], t[3], float(t[4] + R), t[5])
                if first is None:
                    first = d
                last = R + d / 2
                R += d
        if G.contours and first:
            for cc in G.contours:
                for p in cc.points:
                    p.x = float(p.x + first / 2)
        if G.width:
            G.width = max(200, round(G.width + R))
            shift[G.name] = R


def inside(G, F, k):
    def f(x, y):
        pen = PointInsidePen(F, (x, y))
        for c in G.contours[:k]:
            c.draw(pen)
        return pen.getResult()
    return f


def thickness(A, N, allP):
    """Rough stroke thickness at each point: the nearest outline point straight across the ink."""
    out = np.full(len(A), 1e9)
    for i in range(len(A)):
        v = allP - A[i]
        d = np.linalg.norm(v, axis=1) + 1e-9
        ok = (-(v @ N[i]) / d > 0.75) & (d > 8)
        if ok.any():
            out[i] = d[ok].min()
    return out


def pore(cx, cy, rx, ry, ang):
    """The 8-point pore contour as an ellipse (counter-clockwise, so it cuts a hole)."""
    pts = []
    for i in range(4):
        for a, f in ((2 * math.pi * i / 4, 1.0), (2 * math.pi * (i + 0.5) / 4, 1 / math.cos(math.pi / 4))):
            x, y = rx * f * math.cos(a), ry * f * math.sin(a)
            pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    return pts


def wear_glyph(G, F, k, stem):
    rng = glyph_rng(G.name, 11)
    real = [c for c in G.contours[:k] if len(c.points) >= 3]
    if not real:
        return
    allP = np.concatenate([arr(c) for c in real])
    thick = {id(c): thickness(arr(c), geom(arr(c))[0], allP) for c in real}
    for c in real:
        A = arr(c)
        N, s, L, _ = geom(A)
        wob = noise(s, L, stem, rng, [(1.6, 0.5), (0.6, 0.35), (0.25, 0.3)])
        d = stem * WEAR * np.maximum(0, 0.45 + WEAR_WOBBLE * wob)
        chips = np.zeros_like(s)
        for _ in range(max(1, int(CHIPS * L / (0.25 * stem)))):
            s0 = rng.uniform(0, L)
            w = rng.uniform(0.12, 0.3) * stem
            dep = rng.uniform(0.4, 1) * CHIP_DEPTH * stem
            dd = np.abs(s - s0)
            dd = np.minimum(dd, L - dd)
            chips = np.maximum(chips, dep * np.exp(-((dd / w) ** 2)))
        d = np.minimum(d + chips, WEAR_KEEP * thick[id(c)])
        for i, p in enumerate(c.points):
            p.x = float(p.x - N[i, 0] * d[i])
            p.y = float(p.y - N[i, 1] * d[i])
        untangle(c, stem)

    # Open every collapsed pore that sits inside the worn ink: a scratch along the stroke or a speck.
    ins = inside(G, F, k)
    edge = np.concatenate([arr(c) for c in real])
    tang = np.concatenate([np.roll(arr(c), -1, 0) - np.roll(arr(c), 1, 0) for c in real])
    done = []
    for c in G.contours[k:]:
        if not is_dot(c):
            continue
        cx, cy = c.points[0].x, c.points[0].y
        if not ins(cx, cy):
            continue
        j = int(np.argmin(np.hypot(edge[:, 0] - cx, edge[:, 1] - cy)))
        if rng.random() < SCRATCHES:
            ang = math.atan2(tang[j][1], tang[j][0]) + rng.uniform(-0.25, 0.25)
            rx, ry = rng.uniform(0.3, 0.9) * stem, rng.uniform(0.035, 0.09) * stem
        else:
            r, e = rng.uniform(0.06, 0.14) * stem, rng.uniform(1, 1.8)
            rx, ry, ang = r * e, r / e, rng.uniform(0, math.pi)
        for _ in range(6):
            margin = pore(cx, cy, rx * 1.15, ry * 1.15 + 12, ang)
            if all(ins(x, y) for x, y in margin) and all(
                    math.hypot(cx - X, cy - Y) > R + max(rx, ry) + 15 for X, Y, R in done):
                for p, (x, y) in zip(c.points, pore(cx, cy, rx, ry, ang)):
                    p.x, p.y = float(x), float(y)
                done.append((cx, cy, max(rx, ry)))
                break
            rx *= 0.75
            ry = max(ry * 0.9, 10)


def worn(F, stem):
    for G in F:
        if G.contours:
            wear_glyph(G, F, outline_count(G), stem)


def stem_of(F):
    G = F["l"]
    ins = inside(G, F, outline_count(G))
    xs = [x for x in range(-200, G.width + 200, 3) if ins(x, 1000)]
    return (max(xs) - min(xs)) if xs else 300


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="only masters whose file name contains this, e.g. Regular-B0")
    args = ap.parse_args()
    for ds in DESIGNSPACES:
        doc = DesignSpaceDocument.fromfile(SOURCES / ds)
        plain = {}
        for s in doc.sources:
            loc = s.location
            if loc.get("Ink Bleed", 0) == 0 and loc.get("Worn Print", 0) == 0:
                plain[(loc["Weight"], loc["Light Burn"])] = s.path
        for s in doc.sources:
            loc = s.location
            fx = "ink" if loc.get("Ink Bleed", 0) else "worn" if loc.get("Worn Print", 0) else None
            if not fx or (args.only and args.only not in Path(s.path).name):
                continue
            stem = stem_of(ufoLib2.Font.open(plain[(loc["Weight"], 0)]))
            F = ufoLib2.Font.open(plain[(loc["Weight"], loc["Light Burn"])])
            (ink if fx == "ink" else worn)(F, stem)
            F.save(s.path, overwrite=True)
            print(Path(s.path).name, "stem", stem)


if __name__ == "__main__":
    main()
