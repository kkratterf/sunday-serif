"""Per-letter print simulation v2: smooth ink spread, patchy wear; smooth outline fit."""
import math, zlib, numpy as np
from scipy import ndimage as ndi
from sim import raster, fbm, outline_count, SC, pore
from effects_v1 import arr, area, crossings

def loop_ink(loop, sim, org):
    """fraction of sim ink inside a polygon given in font units"""
    from PIL import Image, ImageDraw
    q = (loop - np.array(org)) * SC
    x0, y0 = np.floor(q.min(0)).astype(int) - 1; x1, y1 = np.ceil(q.max(0)).astype(int) + 1
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, sim.shape[1]-1), min(y1, sim.shape[0]-1)
    if x1 <= x0 or y1 <= y0: return 0.5
    im = Image.new('L', (x1-x0+1, y1-y0+1), 0)
    ImageDraw.Draw(im).polygon([(x-x0, y-y0) for x, y in q], fill=1)
    inside = np.array(im, bool)
    if inside.sum() == 0: return 0.5
    return sim[y0:y1+1, x0:x1+1][inside].mean()

def untangle(c, stem, sim=None, org=None, maxfrac=0.34):
    """collapse self-intersection loops whose rendering would disagree with the simulation:
    a reversed loop shows as paper, a same-direction lobe shows as ink"""
    A = arr(c); n = len(A)
    if n < 6: return
    sign = np.sign(area(A))
    for _ in range(8):
        changed = False
        for i in range(n):
            for j, X in crossings(A, i):
                a, b = (i, j) if (j - i) % n <= (i - j) % n else (j, i)
                span = (b - a) % n
                if span < 2 or span > maxfrac * n: continue
                loop = np.array([X] + [A[(a + m) % n] for m in range(1, span + 1)])
                ar = area(loop)
                if sim is not None:
                    f = loop_ink(loop, sim, org)
                    bad = (f > 0.5) if np.sign(ar) != sign else (f < 0.5)
                    if not bad: continue
                elif not (np.sign(ar) != sign and abs(ar) < (0.45*stem)**2): continue
                for m in range(1, span + 1): A[(a + m) % n] = X
                changed = True
        if not changed: break
    for p, (x, y) in zip(c.points, A): p.x, p.y = float(x), float(y)

def poly_normals(S):
    t = np.roll(S, -1, 0) - np.roll(S, 1, 0); t /= np.linalg.norm(t, axis=1)[:, None] + 1e-9
    return np.stack([-t[:, 1], t[:, 0]], 1)

def crossing_t(sdf, org, S, N, reach, n=161):
    ts = np.linspace(-reach, reach, n)
    T = np.full(len(S), np.nan)
    for i in range(len(S)):
        P = S[i][None, :] + ts[:, None] * N[i][None, :]
        v = ndi.map_coordinates(sdf, [(P[:, 1]-org[1])*SC, (P[:, 0]-org[0])*SC], order=1, mode='nearest')
        s = np.sign(v); idx = np.where(s[:-1] != s[1:])[0]
        if len(idx):
            j = idx[np.argmin(np.abs(ts[idx]))]
            T[i] = ts[j] + (ts[j+1]-ts[j]) * v[j] / (v[j]-v[j+1])
    return T

def smooth_wrap(T, L, sig_units):
    """gaussian along the contour, by arc length"""
    n = len(T); s = np.concatenate([[0], np.cumsum(L)])[:n]; tot = s[-1] + L[-1]
    out = np.empty(n)
    for i in range(n):
        d = np.abs(s - s[i]); d = np.minimum(d, tot - d)
        w = np.exp(-0.5 * (d / sig_units) ** 2)
        out[i] = (w * T).sum() / w.sum()
    return out

def fit_contour(c, sdf, org, reach, sig):
    P = c.points; n = len(P)
    on = np.array([p.type is not None for p in P])
    if n < 3 or not on.any(): return
    A = np.array([(p.x, p.y) for p in P])
    # sample points: on-curves as is, off-curves -> curve midpoint (all segments are on,off,on)
    S = A.copy()
    for i in np.where(~on)[0]:
        S[i] = (A[i-1] + 2*A[i] + A[(i+1) % n]) / 4
    N = poly_normals(S)
    T = crossing_t(sdf, org, S, N, reach)
    ok = ~np.isnan(T)
    if not ok.any():
        cen = A.mean(0)
        for p in P: p.x, p.y = float(cen[0]), float(cen[1])
        return
    idx = np.where(ok)[0]
    for i in np.where(~ok)[0]:
        T[i] = T[idx[np.argmin(np.minimum(np.abs(idx-i), n-np.abs(idx-i)))]]
    med = ndi.median_filter(T, size=7, mode='wrap')
    bad = np.abs(T - med) > 0.15 * reach
    T[bad] = med[bad]
    L = np.linalg.norm(np.roll(S, -1, 0) - S, axis=1) + 1e-6
    T = smooth_wrap(T, L, sig)
    S2 = S + T[:, None] * N
    B = S2.copy()
    for i in np.where(~on)[0]:
        B[i] = 2*S2[i] - (S2[i-1] + S2[(i+1) % n]) / 2
    # keep smooth joins smooth (G1)
    for i in np.where(on)[0]:
        a, b = (i-1) % n, (i+1) % n
        if on[a] or on[b]: continue
        u = A[i]-A[a]; v = A[b]-A[i]
        cos = u @ v / (np.linalg.norm(u)*np.linalg.norm(v) + 1e-9)
        if cos > 0.96:
            r = np.linalg.norm(u) / (np.linalg.norm(u) + np.linalg.norm(v) + 1e-9)
            B[i] = B[a] + r * (B[b] - B[a])
    for p, (x, y) in zip(P, B): p.x, p.y = float(x), float(y)

def sdf_of(mask):
    inside = mask > 0.5
    return ndi.distance_transform_edt(~inside) - ndi.distance_transform_edt(inside)

# ---------------- ink: ink soaking into paper, slow and round
IK = dict(sigma=0.42, bias=0.27, noise=0.26, s1=1.4, s2=0.55, a2=0.45, round=0.2, reach=0.26, counter=0.5)
def ink_sim(img, stem_px, rng, amt=1.0):
    b = ndi.gaussian_filter(img, IK['sigma']*stem_px*amt)
    n = fbm(img.shape, rng, [IK['s1']*stem_px, IK['s2']*stem_px], [1.0, IK['a2']])
    n /= n.std() + 1e-9
    f = b + IK['noise']*amt*n*np.clip(b*3, 0, 1)
    m = ((f > 0.5 - IK['bias']*amt) | (ndi.gaussian_filter(img, 0.15*stem_px) > 0.3)).astype(float)
    ink = img > 0.5
    dout = ndi.distance_transform_edt(~ink)
    m = m.astype(bool) & (dout < IK['reach']*stem_px*(1 + 0.35*np.clip(n, -1.5, 1.5)))   # bounded spread: never reaches the neighbours
    lab, nl = ndi.label(~ink)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    for h in range(1, nl+1):                                          # counters keep their heart open
        if h in edge: continue
        hm = lab == h
        dm = dout[hm].max()
        m[hm & (dout > IK['counter']*dm)] = False
    m = (ndi.gaussian_filter(m.astype(float), IK['round']*stem_px) > 0.5)          # surface tension: no kinks
    m |= ndi.gaussian_filter(img, 0.15*stem_px) > 0.3
    m = keep_open(m, img, stem_px)
    m = ndi.gaussian_filter(m.astype(float), 0.08*stem_px) > 0.5
    if IK.get('holes_exact'):                                         # keep every original counter exactly open
        for h in range(1, nl+1):
            if h not in edge: m[lab == h] = False
    lab, _ = ndi.label(m); keep = np.unique(lab[(img > 0.5) & m])
    return np.isin(lab, keep[keep > 0]).astype(float)

def topo(m):
    """(ink pieces, holes)"""
    _, a = ndi.label(m)
    lab, b = ndi.label(~m)
    border = len(set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0})
    return a, b - border

def keep_open(m, img, stem_px):
    """spread ink must not close a notch into a new hole: cut a thin channel back to the paper"""
    from skimage.graph import MCP_Geometric
    out0 = ~(img > 0.5)
    lab0, _ = ndi.label(out0); bl = set(np.unique(np.concatenate([lab0[0], lab0[-1], lab0[:, 0], lab0[:, -1]]))) - {0}
    outside0 = np.isin(lab0, list(bl))
    for _ in range(4):
        lab, n = ndi.label(~m)
        b = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        new = [i for i in range(1, n+1) if i not in b and outside0[lab == i].mean() > 0.5]
        if not new: break
        d = ndi.distance_transform_edt(out0)
        cost = np.where(outside0, 1.0/(d+1.0)**2, 1e6)
        H = lab == new[0]
        mcp = MCP_Geometric(cost)
        starts = np.argwhere(H)[::7]
        cum, _ = mcp.find_costs(starts)
        ends = (~m) & np.isin(lab, list(b))
        tgt = np.unravel_index(np.argmin(np.where(ends, cum, np.inf)), m.shape)
        path = np.array(mcp.traceback(tgt))
        ch = np.zeros_like(m); ch[path[:, 0], path[:, 1]] = True
        ch = ndi.binary_dilation(ch, iterations=max(1, int(0.14*stem_px)))
        m = m & ~ch
    return m

# ---------------- worn: clean edges, a few soft nicks, flecks clustered in worn patches
WK = dict(patch=1.4, cover=0.5, nicks=7, nick=(0.18, 0.42), flecks=44, fleck=(0.035, 0.09))
def worn_plan(img, stem_px, rng, amt=1.0):
    ink = img > 0.5
    patch = fbm(img.shape, rng, [WK['patch']*stem_px], [1.0])
    zone = patch > np.quantile(patch[ink], 1-WK['cover']) if ink.any() else patch > 9
    dist = ndi.distance_transform_edt(ink) / stem_px
    edge = np.argwhere(ink & (dist < 0.08))
    H, W = img.shape; yy, xx = np.mgrid[0:H, 0:W]
    m = ink.copy()
    # nicks: soft round bites into the edge, mostly in worn patches
    if len(edge):
        w = np.where(zone[edge[:, 0], edge[:, 1]], 1.0, 0.15); w /= w.sum()
        nx, ny = np.gradient(ndi.gaussian_filter(ink.astype(float), 2))
        topo0 = topo(m)
        for _ in range(int(round(WK['nicks']*amt))):
            y, x = edge[rng.choice(len(edge), p=w)]
            keep = m.copy()
            g = np.array([ny[y, x], nx[y, x]]); g = -g/(np.linalg.norm(g)+1e-9)   # outward (x, y)
            R = rng.uniform(*WK['nick'])*stem_px*amt
            for _ in range(rng.integers(2, 5)):   # a chip = a few overlapping irregular bites
                r = R*rng.uniform(0.35, 0.8); e = rng.uniform(0.45, 1.0); t = rng.uniform(0, np.pi)
                cx = x + g[0]*r*rng.uniform(0.1, 0.7) + rng.normal(0, 0.45*R)
                cy = y + g[1]*r*rng.uniform(0.1, 0.7) + rng.normal(0, 0.45*R)
                dx, dy = xx-cx, yy-cy; u = dx*np.cos(t)+dy*np.sin(t); v = -dx*np.sin(t)+dy*np.cos(t)
                m &= (u/r)**2 + (v/(r*e))**2 > 1
            if topo(ndi.gaussian_filter(m.astype(float), 0.04*stem_px) > 0.5) != topo0: m = keep   # a chip must not cut a stroke
    m = ndi.gaussian_filter(m.astype(float), 0.04*stem_px) > 0.5
    # flecks: small white specks, in clusters inside worn patches, away from the edge
    fl = []
    d2 = ndi.distance_transform_edt(m) / stem_px
    cand = np.argwhere(zone & (d2 > 0.12))
    if len(cand):
        for _ in range(int(WK['flecks']*amt)*4):
            if len(fl) >= int(WK['flecks']*amt): break
            y, x = cand[rng.integers(len(cand))]
            r = rng.uniform(*WK['fleck'])*stem_px*(0.6+0.4*amt); e = rng.uniform(0.35, 1.0)
            if d2[y, x]*stem_px < r + 0.05*stem_px: continue
            if any((x-a)**2+(y-b)**2 < (r+q+0.04*stem_px)**2 for a, b, q, _, _ in fl): continue
            fl.append((x, y, r, r*e, rng.uniform(0, np.pi)))
    return m.astype(float), fl

def holes(sim, img, org, nmax, minpx=5):
    sp = (img > 0.5) & (sim < 0.5)
    sp = ndi.binary_erosion(img > 0.5, iterations=2) & sp
    lab, n = ndi.label(sp); out = []
    for i in range(1, n+1):
        yy, xx = np.nonzero(lab == i)
        if len(xx) < minpx: continue
        cx, cy = xx.mean(), yy.mean(); C = np.cov(np.stack([xx, yy])) + np.eye(2)*0.25
        w, V = np.linalg.eigh(C); ang = math.atan2(V[1, 1], V[0, 1])
        out.append((len(xx), cx/SC+org[0], cy/SC+org[1], 2*math.sqrt(w[1])/SC, 2*math.sqrt(w[0])/SC, ang))
    out.sort(reverse=True); return out[:nmax]

FIT = 'normal'
def new_holes(G, k, sim, org, nmax, minpx=12):
    """paper enclosed by the spread ink that no counter of the glyph covers: drawn with pores"""
    lab, n = ndi.label(sim < 0.5)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    cens = []
    for c in G.contours[:k]:
        A = np.array([(p.x, p.y) for p in c.points])
        if np.ptp(A[:, 0]) > 1 and np.ptp(A[:, 1]) > 1:
            q = ((A - np.array(org)) * SC).astype(int)
            cens.append(q)
    out = []
    for i in range(1, n+1):
        if i in border: continue
        yy, xx = np.nonzero(lab == i)
        if len(xx) < minpx: continue
        # claimed if an existing contour passes through it
        if any(((lab[np.clip(q[:, 1], 0, lab.shape[0]-1), np.clip(q[:, 0], 0, lab.shape[1]-1)] == i).mean() > 0.3) for q in cens):
            continue
        cx, cy = xx.mean(), yy.mean(); C = np.cov(np.stack([xx, yy])) + np.eye(2)*0.25
        w, V = np.linalg.eigh(C); ang = math.atan2(V[1, 1], V[0, 1])
        out.append((len(xx), cx/SC+org[0], cy/SC+org[1], 2*math.sqrt(w[1])/SC, 2*math.sqrt(w[0])/SC, ang))
    out.sort(reverse=True); return out[:nmax]

def apply(F, names, kind, stem, seed=7, amt=1.0):
    stem_px = stem*SC
    for nm in names:
        G = F[nm]; k = outline_count(G)
        if not G.contours[:k]: continue
        rng = np.random.default_rng(zlib.crc32(nm.encode())+seed)
        img, org = raster(G, k)
        if kind == 'worn':
            for c, (cx, cy, L, w, ang, b) in zip(G.contours[k:], scratches(img, org, stem, rng, len(G.contours)-k, amt)):
                for p, (x, y) in zip(c.points, needle(cx, cy, L, w, ang, b)): p.x, p.y = float(x), float(y)
            continue
        if kind == 'ink': sim = ink_sim(img, stem_px, rng, amt)
        else: sim, fl = worn_plan(img, stem_px, rng, amt)
        sdf = sdf_of(sim) / SC
        reach = (0.75 if kind == 'ink' else 0.6)*stem
        sig = (0.10 if kind == 'ink' else 0.05)*stem
        hs = [(0, x/SC+org[0], y/SC+org[1], rx/SC, ry/SC, t) for x, y, rx, ry, t in fl][:len(G.contours)-k] if kind == 'worn' else []
        if FIT == 'mono':
            fit_mono(G, k, sim, org, stem)
            for c in G.contours[:k]: untangle(c, stem, sim, org)
            pass
        for c in (G.contours[:k] if FIT != 'mono' else []):
            if FIT == 'snake': fit_snake(c, sdf*SC, org, stem)
            else: fit_contour(c, sdf, org, reach, sig)
            untangle(c, stem, sim, org)
        for c, h in zip(G.contours[k:], hs):
            _, cx, cy, rx, ry, ang = h
            for p, (x, y) in zip(c.points, pore(cx, cy, max(rx, 6), max(ry, 5), ang)): p.x, p.y = float(x), float(y)
    return F

# ---------------- snake fit: points flow down the sdf onto the sim boundary
def fit_snake(c, sdf_px, org, stem, iters=80, sig=0.05):
    P = c.points; n = len(P)
    on = np.array([p.type is not None for p in P])
    if n < 3 or not on.any(): return
    A = np.array([(p.x, p.y) for p in P])
    S = A.copy()
    for i in np.where(~on)[0]: S[i] = (A[i-1] + 2*A[i] + A[(i+1) % n]) / 4
    sm = ndi.gaussian_filter(sdf_px, 1.0)
    gy, gx = np.gradient(sm)
    step = 0.06*stem
    def at(F, Q): return ndi.map_coordinates(F, [(Q[:, 1]-org[1])*SC, (Q[:, 0]-org[0])*SC], order=1, mode='nearest')
    L0 = np.linalg.norm(np.roll(S, -1, 0) - S, axis=1)
    for it in range(iters):
        d = at(sm, S) / SC
        g = np.stack([at(gx, S), at(gy, S)], 1); g /= np.linalg.norm(g, axis=1)[:, None] + 1e-9
        S = S - np.clip(d, -step, step)[:, None] * g
        # tangential relaxation keeps the spacing even without shrinking the shape
        mid = (np.roll(S, 1, 0) + np.roll(S, -1, 0)) / 2
        t = np.roll(S, -1, 0) - np.roll(S, 1, 0); t /= np.linalg.norm(t, axis=1)[:, None] + 1e-9
        S = S + 0.3 * np.einsum('ij,ij->i', mid - S, t)[:, None] * t
    # points stuck on a ridge (inside a filled notch): bridge them between their good neighbours
    d = np.abs(at(sm, S) / SC); bad = d > 0.04*stem
    if bad.all(): S[:] = S.mean(0)
    elif bad.any():
        good = np.where(~bad)[0]
        for i in np.where(bad)[0]:
            k = np.searchsorted(good, i); a = good[k-1]; b = good[k % len(good)]
            la = (i - a) % n; lb = (b - i) % n
            S[i] = S[a] + (S[b] - S[a]) * la / (la + lb)
    # light smoothing of positions along the contour
    L = np.linalg.norm(np.roll(S, -1, 0) - S, axis=1) + 1e-6
    S = np.stack([smooth_wrap(S[:, 0], L, sig*stem), smooth_wrap(S[:, 1], L, sig*stem)], 1)
    if abs(area(S)) < (0.08*stem)**2:      # counter closed up
        S[:] = S.mean(0)
    B = S.copy()
    for i in np.where(~on)[0]: B[i] = 2*S[i] - (S[i-1] + S[(i+1) % n]) / 2
    for i in np.where(on)[0]:
        a, b = (i-1) % n, (i+1) % n
        if on[a] or on[b]: continue
        u = A[i]-A[a]; v = A[b]-A[i]
        if u @ v / (np.linalg.norm(u)*np.linalg.norm(v) + 1e-9) > 0.96:
            r = np.linalg.norm(u) / (np.linalg.norm(u) + np.linalg.norm(v) + 1e-9)
            B[i] = B[a] + r * (B[b] - B[a])
    for p, (x, y) in zip(P, B): p.x, p.y = float(x), float(y)

# ---------------- monotone fit: map each contour onto a boundary curve of the sim, in order
from skimage import measure
from scipy.spatial import cKDTree

def pip(pt, poly):
    x, y = pt; X, Y = poly[:, 0], poly[:, 1]; X2, Y2 = np.roll(X, -1), np.roll(Y, -1)
    c = ((Y > y) != (Y2 > y)) & (x < (X2 - X) * (y - Y) / (Y2 - Y + 1e-12) + X)
    return c.sum() % 2 == 1

def targets(sim, org):
    cs = []
    for q in measure.find_contours(ndi.gaussian_filter(np.pad(sim.astype(float), 1), 1.5), 0.5):
        P = np.stack([(q[:, 1]-1)/SC + org[0], (q[:, 0]-1)/SC + org[1]], 1)
        if len(P) < 8: continue
        if np.allclose(P[0], P[-1]): P = P[:-1]
        cs.append(P)
    # outer (even nesting) or hole
    info = []
    for i, P in enumerate(cs):
        depth = sum(pip(P[0], Q) for j, Q in enumerate(cs) if j != i)
        info.append(depth % 2 == 0)
    return cs, info

def resample(P, step):
    L = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1); s = np.concatenate([[0], np.cumsum(L)])
    tot = s[-1]; m = max(int(tot/step), 8); t = np.linspace(0, tot, m, endpoint=False)
    Q = np.concatenate([P, P[:1]])
    return np.stack([np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])], 1)

def pava(y, w):
    """isotonic (non-decreasing) least squares fit"""
    vals, wts, cnt = [], [], []
    for yi, wi in zip(y, w):
        vals.append(yi); wts.append(wi); cnt.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, c2 = vals.pop(), wts.pop(), cnt.pop()
            vals[-1] = (vals[-1]*wts[-1] + v2*w2) / (wts[-1] + w2); wts[-1] += w2; cnt[-1] += c2
    return np.repeat(vals, cnt)

def align(S, T, stem=351.0, wn=6.0):
    """monotone alignment of points S onto polyline T (index non-decreasing, S[0] -> T[0])"""
    n, M = len(S), len(T)
    D = ((S[:, None, :] - T[None, :, :])**2).sum(-1)
    nS, nT = poly_normals(S), poly_normals(T)
    D += wn * stem**2 * (1 - nS @ nT.T) / 2       # don't map a wall onto a wall facing the other way
    D = np.minimum(D, (1.2*stem)**2)              # far points (a closed-up notch) just collapse
    C = D[0].copy(); C[1:] += 1e12
    arg = np.zeros((n, M), np.int32)
    for i in range(1, n):
        cm = np.minimum.accumulate(C)
        am = np.zeros(M, np.int64)
        # index of the running min
        better = np.concatenate([[True], C[1:] < cm[:-1]])
        am = np.maximum.accumulate(np.where(better, np.arange(M), 0))
        arg[i] = am
        C = D[i] + cm
    out = np.empty(n, int); jcur = int(np.argmin(C))
    for i in range(n-1, -1, -1):
        out[i] = jcur
        if i: jcur = arg[i, jcur]
    return out.astype(float)

def fit_mono(G, k, sim, org, stem, sig=0.05, allsmooth=True):
    cs, outer = targets(sim, org)
    cons = G.contours[:k]
    data = []
    for c in cons:
        P = c.points; n = len(P); on = np.array([p.type is not None for p in P])
        A = np.array([(p.x, p.y) for p in P]); S = A.copy()
        for i in np.where(~on)[0]: S[i] = (A[i-1] + 2*A[i] + A[(i+1) % n]) / 4
        data.append((c, on, A, S, area(S)))
    big = max(data, key=lambda d: abs(d[4]))[4]
    osign = np.sign(big)
    T = []
    for P, o in zip(cs, outer):
        P = resample(P, 4.0)
        if np.sign(area(P)) != (osign if o else -osign): P = P[::-1].copy()
        T.append((P, o))
    allp = np.concatenate([P for P, _ in T]) if T else np.zeros((0, 2))
    lab = np.concatenate([[i]*len(P) for i, (P, _) in enumerate(T)]) if T else np.zeros(0, int)
    tree = cKDTree(allp) if len(allp) else None
    for c, on, A, S, ar in data:
        n = len(S)
        if n < 3: continue
        isouter = np.sign(ar) == osign
        cand = [i for i, (_, o) in enumerate(T) if o == isouter]
        ok = False
        if cand and not isouter:
            inside = [i for i in cand if pip(T[i][0].mean(0), S)]
            if inside:
                ti = max(inside, key=lambda i: abs(area(T[i][0]))); Tp = T[ti][0]; M = len(Tp)
                d, j = cKDTree(Tp).query(S); ok = True
        elif cand:
            sub = np.concatenate([T[i][0] for i in cand]); sl = np.concatenate([[i]*len(T[i][0]) for i in cand])
            d, j = cKDTree(sub).query(S)
            votes = np.bincount(sl[j], weights=1/(d+20), minlength=len(T))
            ti = int(np.argmax(votes)); Tp = T[ti][0]; M = len(Tp)
            d, j = cKDTree(Tp).query(S); ok = True
        if not ok:
            cen = S.mean(0); B = np.repeat(cen[None], n, 0)
        else:
            st = int(np.argmin(d)); order = (np.arange(n) + st) % n
            Tr = np.roll(Tp, -int(j[st]), 0)          # target starts at the anchor
            v = align(S[order], Tr, stem)
            # spread runs of points that landed on one spot along the curve: no corners, no chords
            pad = 12
            ext = np.concatenate([v[-pad:] - M, v, v[:pad] + M])
            ext = ndi.gaussian_filter1d(ext, 2.5)
            v = ext[pad:-pad]
            idx = np.empty(n); idx[order] = v + j[st]
            f = idx % M; i0 = np.floor(f).astype(int); w = (f - i0)[:, None]
            S2 = Tp[i0] * (1-w) + Tp[(i0+1) % M] * w
            L = np.linalg.norm(np.roll(S, -1, 0) - S, axis=1) + 1e-6
            S2 = np.stack([smooth_wrap(S2[:, 0], L, sig*stem), smooth_wrap(S2[:, 1], L, sig*stem)], 1)
            B = S2.copy()
            for i in np.where(~on)[0]: B[i] = 2*S2[i] - (S2[i-1] + S2[(i+1) % n]) / 2
            for i in np.where(on)[0]:
                a, b = (i-1) % n, (i+1) % n
                if on[a] or on[b]: continue
                uu = A[i]-A[a]; vv = A[b]-A[i]
                if allsmooth or uu @ vv / (np.linalg.norm(uu)*np.linalg.norm(vv) + 1e-9) > 0.96:
                    r = np.linalg.norm(uu) / (np.linalg.norm(uu) + np.linalg.norm(vv) + 1e-9)
                    B[i] = B[a] + r * (B[b] - B[a])
        for p, (x, y) in zip(c.points, B): p.x, p.y = float(x), float(y)

# ---------------- worn v3: the letter keeps its exact outline; the plate is scratched
SK = dict(angle=-0.21, spread=0.32, lmin=0.5, lmax=2.6, wmin=5, wmax=13, margin=3, minseg=0.12, flecks=0.2)
def needle(cx, cy, L, w, ang, bend):
    pts = []
    rx, ry = L/2, w/2
    for i in range(4):
        for a, f in ((2*math.pi*i/4, 1.0), (2*math.pi*(i+0.5)/4, 1/math.cos(math.pi/4))):
            x, y = rx*f*math.cos(a), ry*f*math.sin(a)
            y += bend * (1 - min(1, (x/rx)**2)) if rx > 0 else 0
            pts.append((cx+x*math.cos(ang)-y*math.sin(ang), cy+x*math.sin(ang)+y*math.cos(ang)))
    return pts

def scratches(img, org, stem, rng, nmax, amt=1.0):
    ink = img > 0.5
    if not ink.any(): return []
    depth = ndi.distance_transform_edt(ink) / SC      # font units to the edge
    ys, xs = np.nonzero(ink)
    out = []
    tries = 0
    while len(out) < nmax and tries < 400:
        tries += 1
        i = rng.integers(len(xs)); cx, cy = xs[i]/SC + org[0], ys[i]/SC + org[1]
        fleck = rng.random() < SK['flecks']
        L = rng.uniform(0.06, 0.18)*stem if fleck else rng.uniform(SK['lmin'], SK['lmax'])*stem
        w = rng.uniform(SK['wmin'], SK['wmax']) * (1.4 if fleck else 1.0)
        a = SK['angle'] + rng.normal(0, SK['spread'])
        t = np.linspace(-L/2, L/2, max(int(L/4), 8))
        bend = rng.normal(0, 0.03)*L
        P = np.stack([cx + t*math.cos(a) - bend*(1-(2*t/L)**2)*math.sin(a), cy + t*math.sin(a) + bend*(1-(2*t/L)**2)*math.cos(a)], 1)
        d = ndi.map_coordinates(depth, [(P[:, 1]-org[1])*SC, (P[:, 0]-org[0])*SC], order=1)
        ok = d > w/2 + SK['margin']
        # split into runs inside the ink: each run becomes one needle
        runs, cur = [], []
        for k_, o in enumerate(ok):
            if o: cur.append(k_)
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        for r in runs:
            if len(out) >= nmax: break
            seg = P[r]; Ls = np.linalg.norm(seg[-1]-seg[0])
            if Ls < (0.03 if fleck else SK['minseg'])*stem: continue
            m = seg.mean(0); ang = math.atan2(seg[-1][1]-seg[0][1], seg[-1][0]-seg[0][0])
            # bow of this run, measured from the chord
            nrm = np.array([-math.sin(ang), math.cos(ang)])
            mid = seg[len(seg)//2]; b = float((mid - (seg[0]+seg[-1])/2) @ nrm)
            ww = min(w, 2*(d[r].min() - SK['margin']))
            out.append((m[0], m[1], Ls + ww*0.5, ww*amt, ang, b))
    return out
