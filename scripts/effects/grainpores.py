"""Worn Print grain: add a shared set of small irregular holes (dust and grain) to every glyph.
The holes are 4-point all-off-curve quadratic blobs appended after the existing pores. They are
open only in the Worn100 masters and collapse to a single point everywhere else.
Placement follows the photo-style distress model: more holes near the edges (grain), clusters
in starved patches, a power-law size distribution (many tiny, a few medium).
usage: grainpores.py STYLEDIR PREFIX [glyph ...]"""
import sys, math, re, zlib, glob, os
import numpy as np, ufoLib2
from multiprocessing import Pool
from scipy import ndimage as ndi
from fontTools.pens.freetypePen import FreeTypePen
from fontTools.pens.transformPen import TransformPen
from ufoLib2.objects import Contour, Point
from scipy.spatial import cKDTree
from flat import sample_contour

SC = 1 / 2; PAD = 200
W3 = ['Regular', 'Medium', 'SemiBold']
STEM = 354
MARGIN = 7
src, pre = sys.argv[1], sys.argv[2]
only = set(sys.argv[3:])
paths = sorted(glob.glob(os.path.join(src, pre + '*.ufo')))

def key(p):
    m = re.match(re.escape(pre) + r'(Regular|Medium|SemiBold)-B(\d+)(?:-(Ink100|Worn100))?\.ufo', os.path.basename(p))
    return m.group(1), int(m.group(2)), m.group(3)

# Only the drawn weights (today: Regular; Bold is derived by scripts/derive_weight.py).
paths = [p for p in paths if re.match(re.escape(pre) + r'(Regular|Medium|SemiBold)-B\d+', os.path.basename(p))]
W3 = [w for w in W3 if any(key(p)[0] == w for p in paths)]

def blob(cx, cy, r, e, ang, jit):
    """4 off-curve points; the quadratic curve passes through their midpoints"""
    pts = []
    for k in range(4):
        a = ang + k * math.pi / 2
        R = r * math.sqrt(2) * jit[k] * (e if k % 2 else 1.0)
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts

def curve(pts, n=6):
    out = []
    for k in range(4):
        p0 = np.add(pts[k - 1], pts[k]) / 2; p1 = np.array(pts[k]); p2 = np.add(pts[k], pts[(k + 1) % 4]) / 2
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append((1 - t) ** 2 * p0 + 2 * t * (1 - t) * p1 + t * t * p2)
    return np.array(out)

def raster(contours, box):
    x0, y0, W, H = box
    pen = FreeTypePen(None); tp = TransformPen(pen, (SC, 0, 0, SC, -x0 * SC, -y0 * SC))
    for c in contours: c.draw(tp)
    return np.flipud(pen.array(width=W, height=H)) > 0.5

def clear(a): return ndi.distance_transform_edt(a) / SC

def fits(TR, INK, box, C, margin):
    x0, y0, W, H = box
    j = ((C[:, 0] - x0) * SC).astype(int); i = ((C[:, 1] - y0) * SC).astype(int)
    if (i < 0).any() or (i >= H).any() or (j < 0).any() or (j >= W).any() or not INK[i, j].all(): return False
    return TR.query(C)[0].min() >= margin

def at(D, box, P):
    x0, y0, W, H = box
    j = ((P[:, 0] - x0) * SC).astype(int); i = ((P[:, 1] - y0) * SC).astype(int)
    ok = (i >= 0) & (i < H) & (j >= 0) & (j < W)
    v = np.zeros(len(P)); v[ok] = D[i[ok], j[ok]]
    return v

def noise(shape, rng, s):
    n = ndi.gaussian_filter(rng.standard_normal(shape), s)
    return n / (n.std() + 1e-9)

FW = None
def init():
    global FW
    FW = {key(p): ufoLib2.Font.open(p) for p in paths}

DENS = float(os.environ.get('DENS', '1.0'))
def kind_params(kind, rng):
    if kind == 'edge':   # grain eating the edge: tiny holes hugging the outline
        return min(9.0 * rng.random() ** (-1 / 1.6), 36.0), 1.0, 3
    if kind == 'patch':  # starved patch: a dense cluster of tiny holes
        return min(8.0 * rng.random() ** (-1 / 1.8), 24.0), 3.0, 3
    return min(9.0 * rng.random() ** (-1 / 1.5), 60.0), 7.0, 10   # dust

def plan(gname):
    F = FW
    gs = {k: f[gname] for k, f in F.items() if gname in f}
    g0 = gs[('Regular', 0, None)]
    if len(gs) != len(F) or not g0.contours: return gname, None
    P = [(p.x, p.y) for g in gs.values() for c in g.contours for p in c.points]
    xs, ys = zip(*P)
    x0, y0 = min(xs) - PAD, min(ys) - PAD
    box = (x0, y0, int((max(xs) - x0 + PAD) * SC) + 1, int((max(ys) - y0 + PAD) * SC) + 1)
    try:
        base = raster(g0.contours, box)
        D = {}; TR = {}; INK = {}
        for w in W3:
            for b in (0, 100):
                cs = [c for c in gs[(w, b, 'Worn100')].contours if len({(p.x, p.y) for p in c.points}) > 1]
                a = raster(cs, box); INK[(w, b)] = a; D[(w, b)] = clear(a)
                TR[(w, b)] = cKDTree(np.vstack([sample_contour(c, 2.0)[0] for c in cs]))
    except Exception as e:
        return gname, 'skip ' + str(e)
    area = base.sum() / SC ** 2
    rng = np.random.default_rng(zlib.crc32((pre + 'grain' + gname).encode()))
    N = int(min(300, round(area / STEM ** 2 * 26 * DENS * rng.uniform(0.85, 1.15))))
    if N < 1: return gname, None
    d = ndi.distance_transform_edt(base) / SC
    inner = D[('Regular', 0)]
    patch = noise(base.shape, rng, 0.45 * STEM * SC) + 0.5 * noise(base.shape, rng, 0.2 * STEM * SC)
    maps = {
        'edge': np.exp(-((d - 0.05 * STEM) / (0.04 * STEM)) ** 2) * (inner > 3),
        'patch': np.clip(patch - 1.0, 0, None) * (inner > 6),
        'dust': (inner > 14).astype(float),
    }
    share = {'edge': 0.55, 'patch': 0.3, 'dust': 0.15}
    prob = {}
    for k, m in maps.items():
        f = m.ravel(); s_ = f.sum()
        if s_ > 0: prob[k] = f / s_
    placed = []
    for kind, frac in share.items():
        if kind not in prob: continue
        n_k = int(round(N * frac)); got = 0
        cands = rng.choice(len(prob[kind]), size=max(n_k * 20, 1), p=prob[kind])
        if kind == 'edge':  # bites: the hole hugs the outline, so it reads as the edge being eaten
            ii, jj = np.nonzero(inner > 1.5)
            dv = inner[ii, jj]
        for k in cands:
            if got >= n_k: break
            r, margin, gap = kind_params(kind, rng)
            if kind == 'edge':
                sel = np.nonzero(np.abs(dv - (r * rng.uniform(0.6, 0.9) + margin)) < 1.0)[0]
                if not len(sel): continue
                q = sel[rng.integers(len(sel))]; i, j = ii[q], jj[q]
            else:
                i, j = divmod(k, base.shape[1])
            cx, cy = x0 + (j + rng.random()) / SC, y0 + (i + rng.random()) / SC
            e = rng.uniform(0.5, 1.0); ang = rng.uniform(0, math.pi); jit = rng.uniform(0.7, 1.3, 4)
            if any(abs(cx - px) < r + pr + gap and math.hypot(cx - px, cy - py) < r + pr + gap for px, py, pr, *_ in placed): continue
            C = curve(blob(cx, cy, r, e, ang, jit))
            if not fits(TR[('Regular', 0)], INK[('Regular', 0)], box, C, margin): continue
            fit = {}
            for w in W3:
                fit[(w, 0)] = 1.0 if fits(TR[(w, 0)], INK[(w, 0)], box, C, margin) else 0.0
                fit[(w, 100)] = 0.0
                if fit[(w, 0)]:
                    for sc in (1.0, 0.75, 0.5):
                        if fits(TR[(w, 100)], INK[(w, 100)], box, curve(blob(cx, cy, r * sc, e, ang, jit)), margin):
                            fit[(w, 100)] = sc; break
            placed.append((cx, cy, r, e, ang, tuple(jit), fit)); got += 1
    return gname, placed

def main():
    F = {key(p): ufoLib2.Font.open(p) for p in paths}
    print(len(F), 'masters', flush=True)
    names = [n for n in F[('Regular', 0, None)].keys() if not only or n in only]
    with Pool(4, initializer=init) as pool:
        res = pool.map(plan, names, chunksize=4)
    total = 0
    for gname, placed in res:
        if isinstance(placed, str): print(gname, placed); continue
        if not placed: continue
        total += len(placed)
        for (w, b, fx), f in F.items():
            g = f[gname]
            for cx, cy, r, e, ang, jit, fit in placed:
                sc = fit[(w, b)] if fx == 'Worn100' else 0.0
                pts = blob(cx, cy, r * sc, e, ang, jit) if sc else [(cx, cy)] * 4
                g.contours.append(Contour(points=[Point(float(round(x, 2)), float(round(y, 2)), None) for x, y in pts]))
    print('grain holes', total, 'in', sum(1 for _, p in res if p and not isinstance(p, str)), 'glyphs', flush=True)
    for f in F.values(): f.save()

if __name__ == '__main__':
    main()
