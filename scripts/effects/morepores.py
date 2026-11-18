"""Add more Worn Print pores in the style of the original ones.
usage: morepores.py SRCDIR(style dir with UFOs) PREFIX(SundaySerif- or SundaySerif-Italic-) DENSITY"""
import sys, math, re, zlib, glob, os
import numpy as np, ufoLib2
from scipy.ndimage import distance_transform_edt
from fontTools.pens.freetypePen import FreeTypePen
from fontTools.pens.transformPen import TransformPen
from ufoLib2.objects import Contour, Point

SC = 1/4; PAD = 600
W3 = ['Regular', 'Medium', 'SemiBold']
src, pre, dens = sys.argv[1], sys.argv[2], float(sys.argv[3])
paths = sorted(glob.glob(os.path.join(src, pre + '*.ufo')))
def key(p):
    m = re.match(re.escape(pre) + r'(Regular|Medium|SemiBold)-B(\d+)(?:-(Ink100|Worn100))?\.ufo', os.path.basename(p))
    return m.group(1), int(m.group(2)), m.group(3)

# Only the drawn weights (today: Regular; Bold is derived by scripts/derive_weight.py).
paths = [p for p in paths if re.match(re.escape(pre) + r'(Regular|Medium|SemiBold)-B\d+', os.path.basename(p))]
W3 = [w for w in W3 if any(key(p)[0] == w for p in paths)]
F = {key(p): ufoLib2.Font.open(p) for p in paths}
print(len(F), 'masters')

def ispore(c): return len(c.points) == 8 and all((p.type is None) == (i % 2 == 1) for i, p in enumerate(c.points))
def vis(c): return max(p.x for p in c.points) - min(p.x for p in c.points) > 1
def npores(g):
    n = 0
    for c in reversed(g.contours):
        if ispore(c): n += 1
        else: break
    return n
def pore(cx, cy, rx, ry, ang):
    pts = []
    for i in range(4):
        for a, f in ((2*math.pi*i/4, 1.0), (2*math.pi*(i+0.5)/4, 1/math.cos(math.pi/4))):
            x, y = rx*f*math.cos(a), ry*f*math.sin(a)
            pts.append((cx+x*math.cos(ang)-y*math.sin(ang), cy+x*math.sin(ang)+y*math.cos(ang)))
    return pts
def clearance(g):
    P = [(p.x, p.y) for c in g.contours for p in c.points]
    if not P: return None
    xs, ys = zip(*P)
    x0, y0 = min(xs)-PAD, min(ys)-PAD
    W, H = int((max(xs)-x0+PAD)*SC)+1, int((max(ys)-y0+PAD)*SC)+1
    pen = FreeTypePen(None); tp = TransformPen(pen, (SC, 0, 0, SC, -x0*SC, -y0*SC))
    for c in g.contours: c.draw(tp)
    a = np.flipud(pen.array(width=W, height=H)) > 0.5
    d = distance_transform_edt(a) / SC
    return a, d, (x0, y0)
def clear_at(D, x, y):
    a, d, (x0, y0) = D
    i, j = int((y-y0)*SC), int((x-x0)*SC)
    if 0 <= i < d.shape[0] and 0 <= j < d.shape[1]: return d[i, j]
    return 0
def fits(D, cx, cy, rx, ry, ang, m):
    cs = []
    for t in np.linspace(0, 2*math.pi, 20, endpoint=False):
        x, y = rx*math.cos(t), ry*math.sin(t)
        px, py = cx+x*math.cos(ang)-y*math.sin(ang), cy+x*math.sin(ang)+y*math.cos(ang)
        c = clear_at(D, px, py)
        if c < m: return None
        cs.append(c)
    return min(cs)

base = F[('Regular', 0, None)]
total_new = 0
for gname in base.keys():
    gs = {k: f[gname] for k, f in F.items() if gname in f}
    if len(gs) != len(F): continue
    g0 = gs[('Regular', 0, None)]
    if not g0.contours: continue
    np0 = npores(gs[('Regular', 0, 'Worn100')])
    nb = len(g0.contours) - np0
    if any(len(g.contours) != nb + np0 for g in gs.values()): print('skip mismatch', gname); continue
    slots = list(range(nb, nb+np0))
    owner = {}
    for s in slots:
        o = [w for w in W3 if vis(gs[(w, 0, 'Worn100')].contours[s])]
        owner[s] = o[0] if o else None
    rng = np.random.default_rng(zlib.crc32((pre+gname).encode()))
    new = {w: [] for w in W3}
    for w in W3:
        gw0, gw1 = gs[(w, 0, 'Worn100')], gs[(w, 100, 'Worn100')]
        try:
            D0 = clearance(gw0); D1 = clearance(gw1)
        except Exception as e:
            print('skip', gname, e); continue
        if D0 is None: continue
        area = D0[0].sum() / SC**2
        have = sum(1 for s in slots if owner[s] == w)
        target = int(round(area * dens * rng.uniform(0.8, 1.2)))
        if area > 3e5: target = max(target, have + 1)
        k = target - have
        tries = 0
        while k > 0 and tries < 400:
            tries += 1
            a, d, (x0, y0) = D0
            ys, xs = np.nonzero((d > 25) & (d < 160))
            if not len(xs): break
            i = rng.integers(len(xs)); cx, cy = x0 + (xs[i]+.5)/SC, y0 + (ys[i]+.5)/SC
            rx = rng.uniform(55, 140) * (1.1 if w == 'SemiBold' else 1.0)
            ry = rx * rng.uniform(0.25, 0.42)
            ang = math.radians(rng.normal(0, 16))
            if fits(D0, cx, cy, rx + 12, ry + 12, ang, 14) is None:
                continue
            ok = None
            for sc in (2.5, 2.0, 1.6, 1.3):
                if fits(D1, cx, cy, rx*sc + 12, ry*sc + 12, ang, 14) is not None: ok = sc; break
            if ok is None: continue
            new[w].append(((cx, cy, rx, ry, ang), ok))
            # punch it into the clearance maps so the next one keeps its distance
            for DD, s in ((D0, 1.0), (D1, ok)):
                gtmp = Contour(points=[Point(x, y, 'qcurve' if j % 2 == 0 else None) for j, (x, y) in enumerate(pore(cx, cy, (rx+30)*s, (ry+30)*s, ang))])
                A, dd, (X0, Y0) = DD
                yy, xx = np.mgrid[0:A.shape[0], 0:A.shape[1]]
                X = X0 + (xx+.5)/SC - cx; Y = Y0 + (yy+.5)/SC - cy
                u = X*math.cos(ang) + Y*math.sin(ang); v = -X*math.sin(ang) + Y*math.cos(ang)
                A[(u/((rx+30)*s))**2 + (v/((ry+30)*s))**2 <= 1] = False
                DD[1][:] = distance_transform_edt(A) / SC
            k -= 1
    if not any(new.values()): continue
    # insert after each weight's group: Regular, Medium, SemiBold order
    pos = {}
    last = {w: max([s for s in slots if owner[s] == w], default=None) for w in W3}
    end = nb + np0
    insert_at = {'SemiBold': end, 'Medium': (last.get('Medium')+1 if last.get('Medium') is not None else (min([s for s in slots if owner[s] == 'SemiBold'], default=end))),
                 'Regular': (last.get('Regular')+1 if last.get('Regular') is not None else nb)}
    for (w, b, fx), g in gs.items():
        add = []
        for ww in reversed(W3):  # insert from the back so indexes stay valid
            items = []
            for (cx, cy, rx, ry, ang), s1 in new[ww]:
                t = b / 100
                if fx == 'Worn100' and w == ww:
                    s = 1 + (s1 - 1) * t
                    pts = pore(cx, cy, rx*s, ry*s, ang)
                else:
                    pts = [(cx, cy)] * 8
                items.append(Contour(points=[Point(float(round(x, 2)), float(round(y, 2)), 'qcurve' if j % 2 == 0 else None) for j, (x, y) in enumerate(pts)]))
            at = insert_at[ww]
            g.contours[at:at] = items
    total_new += sum(len(v) for v in new.values())
print('new pores', total_new)
for f in F.values(): f.save()
