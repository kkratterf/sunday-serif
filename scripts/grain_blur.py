"""Generate the Sunday Serif Grain masters (sources/Grain/) from the Regular masters.

usage: python scripts/grain_blur.py

Sunday Serif Grain has one axis, Grain Blur (GRAN 0...100): a blur made of grain, like a
dithered photo. Every glyph gets a cloud of small ink dots (4-point quadratic blobs) after its
outline. At GRAN 0 each dot sits collapsed on the outline, so the letter is plain. At GRAN 100
the outline pulls in a little and the dots spread outwards, dense at the edge and sparse far
away (a half-normal falloff, like a Gaussian blur sampled by grain). Advance widths never change.

Run it again after a design change to the Regular Light Burn 0 masters. The result is
deterministic: every glyph seeds its own random generator from its name.
"""
import math
import shutil
import zlib
from pathlib import Path

import numpy as np
import ufoLib2
from ufoLib2.objects import Contour, Point

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
OUT = SOURCES / "Grain"
STEM = 354            # Regular stem, font units (UPM 4096)
SIGMA = 0.45 * STEM   # spread of the halo
INSET = 0.11 * STEM   # how far the solid core pulls in at GRAN 100
PER_UNIT = 0.14       # dots per unit of outline length
MAX_DOTS = 1000       # per glyph (file size)
STYLES = [  # (source master, output prefix, style name)
    (SOURCES / "Roman" / "SundaySerif-Regular-B0.ufo", "SundaySerifGrain", "Regular"),
    (SOURCES / "Italic" / "SundaySerif-Italic-Regular-B0.ufo", "SundaySerifGrain-Italic", "Italic"),
]


def collapsed(c):
    return len({(p.x, p.y) for p in c.points}) == 1


def area(c):
    x = np.array([p.x for p in c.points]); y = np.array([p.y for p in c.points])
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def flatten(c, step=6.0):
    """Points along a quadratic contour (about `step` units apart) and their unit tangents."""
    pts = [(p.x, p.y, p.type) for p in c.points]
    k0 = next((i for i, p in enumerate(pts) if p[2] is not None), 0)
    ring = pts[k0:] + pts[:k0]
    cur = np.array(ring[0][:2], float)
    out, offs = [], []
    for x, y, t in ring[1:] + ring[:1]:
        q = np.array((x, y), float)
        if t is None:
            offs.append(q)
            continue
        if not offs:
            n = max(1, int(np.linalg.norm(q - cur) / step))
            out += [cur + (q - cur) * s for s in np.linspace(0, 1, n, endpoint=False)]
        else:
            ons = [cur] + [(offs[j] + offs[j + 1]) / 2 for j in range(len(offs) - 1)] + [q]
            for j, c1 in enumerate(offs):
                a, b = ons[j], ons[j + 1]
                n = max(2, int((np.linalg.norm(c1 - a) + np.linalg.norm(b - c1)) / step))
                out += [(1 - s) ** 2 * a + 2 * s * (1 - s) * c1 + s * s * b for s in np.linspace(0, 1, n, endpoint=False)]
        offs, cur = [], q
    A = np.array(out)
    T = np.roll(A, -1, 0) - np.roll(A, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    return A, T


def blob(cx, cy, r, e, ang, jit):
    """4 off-curve points; the quadratic curve runs through their midpoints (about radius r)."""
    pts = []
    for k in range(4):
        a = ang + k * math.pi / 2
        R = r * math.sqrt(2) * jit[k] * (e if k % 2 else 1.0)
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts


def contour(pts, types=None):
    types = types or [None] * len(pts)
    return Contour(points=[Point(float(round(x, 2)), float(round(y, 2)), t) for (x, y), t in zip(pts, types)])


def grain(name, outline):
    """(core outline at GRAN 100, dots at GRAN 0, dots at GRAN 100) for one glyph."""
    rng = np.random.default_rng(zlib.crc32(("grainblur" + name).encode()))
    big = max(outline, key=lambda c: abs(area(c)))
    sign = 1.0 if area(big) < 0 else -1.0  # ink lies on the right of clockwise outer contours
    core = []
    for c in outline:
        P = np.array([(p.x, p.y) for p in c.points], float)
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
        T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
        inward = np.stack([T[:, 1], -T[:, 0]], 1) * sign
        core.append(contour(P + inward * INSET, [p.type for p in c.points]))
    samples = [flatten(c) for c in outline]
    lengths = np.array([len(A) * 6.0 for A, _ in samples])
    n = int(min(MAX_DOTS, lengths.sum() * PER_UNIT))
    cum = np.cumsum(lengths) / lengths.sum()
    d0, d1 = [], []
    for _ in range(n):
        A, T = samples[int(np.searchsorted(cum, rng.random()))]
        k = rng.integers(len(A))
        out = np.array([-T[k, 1], T[k, 0]]) * sign
        # offset from the edge: most dots fall outside (half-normal), some inside the inset band
        o = abs(rng.normal(0, SIGMA)) if rng.random() > 0.3 else -rng.uniform(0, INSET)
        o *= rng.uniform(0.8, 1.0)
        side = np.array([-out[1], out[0]]) * rng.normal(0, 0.04 * STEM)
        far = min(max(o, 0) / (2.5 * SIGMA), 1)
        r = rng.uniform(12, 28) * (1 - 0.55 * far)
        e, ang, jit = rng.uniform(0.6, 1.0), rng.uniform(0, math.pi), rng.uniform(0.75, 1.25, 4)
        p = A[k] + out * o + side
        pts = blob(p[0], p[1], r, e, ang, jit)
        d0.append(contour([tuple(A[k])] * 4))
        d1.append(contour(pts if sign > 0 else pts[::-1]))
    return core, d0, d1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for src, prefix, style in STYLES:
        paths = [OUT / f"{prefix}-G0.ufo", OUT / f"{prefix}-G100.ufo"]
        for p in paths:
            shutil.rmtree(p, ignore_errors=True)
            shutil.copytree(src, p)
        f0, f1 = (ufoLib2.Font.open(p) for p in paths)
        for f, s in ((f0, style), (f1, "Grain 100" if style == "Regular" else "Grain 100 Italic")):
            f.info.familyName = "Sunday Serif Grain"
            f.info.styleName = s
        count = 0
        for g0 in f0:
            g1 = f1[g0.name]
            outline = [c for c in g0.contours if not collapsed(c)]  # drop the Worn Print pores
            if not outline:
                g0.contours[:] = []
                g1.contours[:] = []
                continue
            core, d0, d1 = grain(g0.name, outline)
            g0.contours[:] = [contour([(p.x, p.y) for p in c.points], [p.type for p in c.points]) for c in outline] + d0
            g1.contours[:] = core + d1
            count += len(d0)
        f0.save(overwrite=True)
        f1.save(overwrite=True)
        print(f"{prefix}: {count} grain dots")


if __name__ == "__main__":
    main()
