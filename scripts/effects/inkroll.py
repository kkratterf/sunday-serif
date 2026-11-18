"""Densify every master the same way and redraw the Ink100 masters from a per-glyph ink simulation.
usage: inkroll.py STYLEDIR PREFIX [glyph ...]"""
import sys, os, re, glob, zlib, copy, time
import numpy as np, ufoLib2
from multiprocessing import Pool
from ufoLib2.objects import Contour, Point
import sim, sim2, dens
sim2.FIT = 'mono'
STEM = {'Regular': 354, 'Medium': 414, 'SemiBold': 474}
import os
LMAX = float(os.environ.get("LMAX", 70))
src, pre = sys.argv[1], sys.argv[2]; only = set(sys.argv[3:])
paths = sorted(glob.glob(os.path.join(src, pre + '*.ufo')))
def key(p):
    m = re.match(re.escape(pre) + r'(Regular|Medium|SemiBold)-B(\d+)(?:-(Ink100|Worn100))?\.ufo', os.path.basename(p))
    return m.group(1), int(m.group(2)), m.group(3)

# Only the drawn weights (today: Regular; Bold is derived by scripts/derive_weight.py).
paths = [p for p in paths if re.match(re.escape(pre) + r'(Regular|Medium|SemiBold)-B\d+', os.path.basename(p))]
STEM = {w: v for w, v in STEM.items() if any(key(p)[0] == w for p in paths)}
F = {key(p): ufoLib2.Font.open(p) for p in paths}
ref = F[('Regular', 0, None)]

def pts(c): return [(p.x, p.y, p.type) for p in c.points]
def job(args):
    gname, w, b, base = args        # base: list of contours (point lists) of the plain master, densified
    G = ufoLib2.objects.Glyph(gname)
    for cp in base:
        c = Contour(points=[Point(x, y, t) for x, y, t in cp]); G.contours.append(c)
    k = len(G.contours)
    stem = STEM[w]
    rng = np.random.default_rng(zlib.crc32((pre + gname + w + str(b)).encode()) + 7)
    try:
        img, org = sim.raster(G, k)
        sim2.IK['counter'] = 0.5 if b == 0 else 0.0   # Light Burn 100 counters are already thin: keep them
        sim2.IK['holes_exact'] = b == 100
        s = sim2.ink_sim(img, stem*sim.SC, rng, 1.0 if b == 0 else 0.4)
        sim2.fit_mono(G, k, s, org, stem)
        for c in G.contours[:k]: sim2.untangle(c, stem, s, org)
    except Exception as e:
        return gname, w, b, None, repr(e)
    return gname, w, b, [pts(c) for c in G.contours[:k]], None

if __name__ == '__main__':
    t0 = time.time(); jobs = []; K = {}
    for gname in ref.keys():
        if only and gname not in only: continue
        gs = {kk: f[gname] for kk, f in F.items() if gname in f}
        if len(gs) != len(F): continue
        k = sim.outline_count(ref[gname])
        if k == 0: continue
        n = len(ref[gname].contours)
        if any(len(g.contours) != n for g in gs.values()): print('skip mismatch', gname); continue
        for i in range(k):
            pl = dens.plan(ref[gname].contours[i], LMAX)
            for g in gs.values(): dens.apply_plan(g.contours[i], pl)
        if any(len(g.contours[i].points) != len(ref[gname].contours[i].points) for g in gs.values() for i in range(k)):
            print('incompatible after densify', gname); continue
        K[gname] = k
        for w in STEM:
            # Light Burn 100 is already a saturated blot: its Ink100 master is the plain one
            for c, d in zip(F[(w, 100, 'Ink100')][gname].contours[:k], F[(w, 100, None)][gname].contours[:k]):
                for p, q in zip(c.points, d.points): p.x, p.y = q.x, q.y
            for b in (0,):
                jobs.append((gname, w, b, [pts(c) for c in F[(w, b, None)][gname].contours[:k]]))
    print(len(jobs), 'jobs', round(time.time()-t0), 's'); sys.stdout.flush()
    bad = []
    with Pool(4) as pool:
        for i, (gname, w, b, out, err) in enumerate(pool.imap_unordered(job, jobs, chunksize=2)):
            if out is None:
                bad.append((gname, w, b, err)); out = jobs[[j[:3] for j in jobs].index((gname, w, b))][3]
            g = F[(w, b, 'Ink100')][gname]
            for c, cp in zip(g.contours[:K[gname]], out):
                for p, (x, y, t) in zip(c.points, cp): p.x, p.y = float(round(x, 2)), float(round(y, 2))
            if i % 100 == 0: print(i, round(time.time()-t0), 's'); sys.stdout.flush()
    print('failed', len(bad), bad[:10])
    for f in F.values(): f.save()
    print('done', round(time.time()-t0), 's')
