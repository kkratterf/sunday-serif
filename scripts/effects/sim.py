"""Per-letter print simulation: rasterize, simulate ink/wear, pull the outline points onto it."""
import math, zlib, numpy as np, ufoLib2
from scipy import ndimage as ndi
from fontTools.pens.freetypePen import FreeTypePen
from fontTools.pens.transformPen import TransformPen
SC = 1/6.0          # px per font unit
PAD = 400           # font units

def is_dot(c): return len({(p.x, p.y) for p in c.points}) == 1
def outline_count(G):
    k = len(G.contours)
    while k and len(G.contours[k-1].points) == 8 and is_dot(G.contours[k-1]): k -= 1
    return k

def raster(G, k):
    xs = [p.x for c in G.contours[:k] for p in c.points]; ys = [p.y for c in G.contours[:k] for p in c.points]
    x0, y0 = min(xs)-PAD, min(ys)-PAD; x1, y1 = max(xs)+PAD, max(ys)+PAD
    W, H = int((x1-x0)*SC)+1, int((y1-y0)*SC)+1
    pen = FreeTypePen(None)
    for c in G.contours[:k]: c.draw(pen)
    img = pen.array(width=(x1-x0), height=(y1-y0), transform=(SC, 0, 0, SC, -x0*SC, -y0*SC), contain=False, evenOdd=False) if False else None
    pen2 = FreeTypePen(None); tp = TransformPen(pen2, (SC, 0, 0, SC, -x0*SC, -y0*SC))
    for c in G.contours[:k]: c.draw(tp)
    a = pen2.array(width=W, height=H)  # row 0 = top
    return np.flipud(a).astype(float), (x0, y0)   # row 0 = y0 (bottom)

def fbm(shape, rng, scales, amps):
    out = np.zeros(shape)
    for s, a in zip(scales, amps):
        n = rng.standard_normal(shape)
        n = ndi.gaussian_filter(n, s); n /= n.std()+1e-9
        out += a*n
    return out

def to_px(x, y, org): return (x-org[0])*SC, (y-org[1])*SC
def sample(F, px, py):
    return ndi.map_coordinates(F, [[py], [px]], order=1, mode='nearest')[0]

def normals(A):
    t = np.roll(A, -1, 0)-np.roll(A, 1, 0); t /= np.linalg.norm(t, axis=1)[:, None]+1e-9
    return np.stack([-t[:, 1], t[:, 0]], 1)   # outward

def fit(G, k, sim, org, reach):
    """move every point along its normal to the nearest boundary of sim (sdf zero)"""
    inside = sim > 0.5
    sdf = ndi.distance_transform_edt(~inside) - ndi.distance_transform_edt(inside)   # >0 outside
    ts = np.linspace(-reach, reach, 121)
    for c in G.contours[:k]:
        if len(c.points) < 3: continue
        A = np.array([(p.x, p.y) for p in c.points]); N = normals(A)
        newA = A.copy(); ok = np.zeros(len(A), bool)
        for i in range(len(A)):
            P = A[i][None, :] + ts[:, None]*N[i][None, :]
            px = (P[:, 0]-org[0])*SC; py = (P[:, 1]-org[1])*SC
            v = ndi.map_coordinates(sdf, [py, px], order=1, mode='nearest')
            s = np.sign(v); idx = np.where(s[:-1] != s[1:])[0]
            if len(idx):
                j = idx[np.argmin(np.abs(ts[idx]))]
                t = ts[j] + (ts[j+1]-ts[j])*v[j]/(v[j]-v[j+1])
                newA[i] = A[i]+t*N[i]; ok[i] = True
        if not ok.any():   # shape vanished (closed counter): collapse
            cen = A.mean(0); newA[:] = cen
        else:
            T = np.einsum('ij,ij->i', newA-A, N)
            idx = np.where(ok)[0]
            for i in np.where(~ok)[0]:
                T[i] = T[idx[np.argmin(np.minimum(np.abs(idx-i), len(A)-np.abs(idx-i)))]]
            med = ndi.median_filter(T, size=5, mode='wrap')
            bad = np.abs(T-med) > 0.12*reach/0.6*1.0
            T[bad] = med[bad]
            newA = A + T[:, None]*N
        for p, (x, y) in zip(c.points, newA): p.x, p.y = float(x), float(y)

IK = dict(sigma=0.5, bias=0.3, noise=0.08, s1=0.8, s2=0.12)
WK = dict(sigma=0.04, bias=0.07, noise=0.2, g=0.035, s2=0.1, s3=0.35, speck=0.012)
def ink_sim(img, stem_px, rng, amt=1.0):
    """ink soaking into paper: blur, uneven absorption, threshold low -> blobby merges"""
    b = ndi.gaussian_filter(img, IK['sigma']*stem_px*amt)
    n = fbm(img.shape, rng, [IK['s1']*stem_px, IK['s2']*stem_px], [0.85, 0.15])
    out = (b + IK['noise']*amt*n * np.clip(b*4, 0, 1) > 0.5 - IK['bias']*amt)
    lab, _ = ndi.label(out)   # drop loose drops that don't touch the letter
    keep = np.unique(lab[(img > 0.5) & out]); return np.isin(lab, keep[keep > 0]).astype(float)

def worn_sim(img, stem_px, rng, amt=1.0):
    """worn print: fine paper grain eats the edges and leaves white specks inside"""
    b = ndi.gaussian_filter(img, WK['sigma']*stem_px)
    n = fbm(img.shape, rng, [WK['g']*stem_px, WK['s2']*stem_px, WK['s3']*stem_px], [0.5, 0.3, 0.3])
    out = (b + WK['noise']*amt*n > 0.5 + WK['bias']*amt)
    # sparse specks: rare dips of fine noise inside the ink
    sp = fbm(img.shape, rng, [WK['g']*stem_px*1.5], [1.0])
    out &= ~(sp > 2.6 - 0.4*amt)
    return out.astype(float)

def holes(sim, img, org, nmax):
    """white specks inside the original ink: biggest first -> (cx, cy, rx, ry, ang) in font units"""
    sp = (img > 0.5) & (sim < 0.5)
    sp = ndi.binary_erosion(ndi.binary_dilation(sp, iterations=0) if False else sp)
    lab, n = ndi.label(sp)
    out = []
    for i in range(1, n+1):
        yy, xx = np.nonzero(lab == i)
        if len(xx) < 6: continue
        # must not touch the edge of the original ink
        if (img[np.clip(yy+2, 0, img.shape[0]-1), xx] < 0.5).any() or (img[np.clip(yy-2, 0, None), xx] < 0.5).any() \
           or (img[yy, np.clip(xx+2, 0, img.shape[1]-1)] < 0.5).any() or (img[yy, np.clip(xx-2, 0, None)] < 0.5).any():
            continue
        cx, cy = xx.mean(), yy.mean(); C = np.cov(np.stack([xx, yy])) + np.eye(2)*0.25
        w, V = np.linalg.eigh(C); ang = math.atan2(V[1, 1], V[0, 1])
        out.append((len(xx), cx/SC+org[0], cy/SC+org[1], 2*math.sqrt(w[1])/SC, 2*math.sqrt(w[0])/SC, ang))
    out.sort(reverse=True)
    return out[:nmax]

def pore(cx, cy, rx, ry, ang):
    pts = []
    for i in range(4):
        for a, f in ((2*math.pi*i/4, 1.0), (2*math.pi*(i+0.5)/4, 1/math.cos(math.pi/4))):
            x, y = rx*f*math.cos(a), ry*f*math.sin(a)
            pts.append((cx+x*math.cos(ang)-y*math.sin(ang), cy+x*math.sin(ang)+y*math.cos(ang)))
    return pts

def apply(F, names, kind, stem, seed=7, amt=1.0):
    stem_px = stem*SC
    for nm in names:
        G = F[nm]; k = outline_count(G)
        if not G.contours[:k]: continue
        rng = np.random.default_rng(zlib.crc32(nm.encode())+seed)
        img, org = raster(G, k)
        sim = (ink_sim if kind == 'ink' else worn_sim)(img, stem_px, rng, amt)
        reach = (0.6 if kind == 'ink' else 0.35)*stem
        if kind == 'worn':
            hs = holes(sim, img, org, len(G.contours)-k)
        fit(G, k, sim, org, reach)
        if kind == 'worn':
            pores = [c for c in G.contours[k:]]
            for c, h in zip(pores, hs):
                _, cx, cy, rx, ry, ang = h
                for p, (x, y) in zip(c.points, pore(cx, cy, max(rx, 8), max(ry, 8), ang)): p.x, p.y = float(x), float(y)
    return F
