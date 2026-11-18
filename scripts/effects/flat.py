import numpy as np

def sample_contour(c, step=6.0):
    """flatten one quadratic contour: points, unit tangents"""
    P = [(p.x, p.y, p.type) for p in c.points]
    n = len(P)
    on = [i for i, p in enumerate(P) if p[2] is not None]
    pts = []
    if not on:  # all off-curve
        segs_from = 0; ring = P
    k0 = on[0] if on else 0
    ring = P[k0:] + P[:k0]
    i = 0; cur = np.array(ring[0][:2], float)
    seq = ring[1:] + ring[:1]
    offs = []
    for p in seq:
        q = np.array(p[:2], float)
        if p[2] is None:
            offs.append(q); continue
        if p[2] == 'line' or not offs:
            L = np.linalg.norm(q - cur); m = max(1, int(L / step))
            for t in np.linspace(0, 1, m, endpoint=False): pts.append(cur + (q - cur) * t)
        else:
            ctrl = offs; ons = [cur] + [(ctrl[j] + ctrl[j + 1]) / 2 for j in range(len(ctrl) - 1)] + [q]
            for j, c1 in enumerate(ctrl):
                a, b = ons[j], ons[j + 1]
                L = np.linalg.norm(c1 - a) + np.linalg.norm(b - c1); m = max(2, int(L / step))
                for t in np.linspace(0, 1, m, endpoint=False):
                    pts.append((1 - t) ** 2 * a + 2 * t * (1 - t) * c1 + t * t * b)
        offs = []; cur = q
    A = np.array(pts)
    T = np.roll(A, -1, 0) - np.roll(A, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    return A, T

