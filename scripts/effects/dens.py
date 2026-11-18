from ufoLib2.objects import Point
def explicit(c):
    P=c.points; n=len(P); out=[]
    for i,p in enumerate(P):
        q=P[i-1]
        if p.type is None and q.type is None and n>1:
            out.append(Point((p.x+q.x)/2,(p.y+q.y)/2,'qcurve'))
        out.append(p)
    # rotate so that it starts with an on-curve; fix types of on-curves preceded by on-curve -> 'line'
    return out
def densify(c, times=1, minlen=0):
    if len(c.points)<3 or all(p.type is None for p in c.points): return
    for _ in range(times):
        pts=explicit(c); n=len(pts)
        start=next(i for i,p in enumerate(pts) if p.type)
        pts=pts[start:]+pts[:start]
        segs=[]; cur=[pts[0]]
        for p in pts[1:]+[pts[0]]:
            cur.append(p)
            if p.type: segs.append(cur); cur=[p]
        out=[]
        for s in segs:
            a=s[0]; b=s[-1]
            if len(s)==2:   # line
                out+= [a, Point((a.x+b.x)/2,(a.y+b.y)/2,'line')]
            else:           # quad a,c,b
                c1=s[1]
                out+= [a, Point((a.x+c1.x)/2,(a.y+c1.y)/2,None), Point((a.x+2*c1.x+b.x)/4,(a.y+2*c1.y+b.y)/4,'qcurve'), Point((c1.x+b.x)/2,(c1.y+b.y)/2,None)]
        # fix on-curve types: an on-curve preceded by an off-curve is qcurve, else line
        for i,p in enumerate(out):
            if p.type: p.type='qcurve' if out[i-1].type is None else 'line'
        c.points.clear()
        for p in out: c.points.append(p)

def segments(c):
    """explicit on-curves; returns list of segments, each a list of points starting/ending on-curve"""
    pts=explicit(c); start=next(i for i,p in enumerate(pts) if p.type); pts=pts[start:]+pts[:start]
    segs=[]; cur=[pts[0]]
    for p in pts[1:]+[pts[0]]:
        cur.append(p)
        if p.type: segs.append(cur); cur=[p]
    return segs
def plan(c, lmax):
    import math
    out=[]
    for s in segments(c):
        L=sum(math.hypot(b.x-a.x,b.y-a.y) for a,b in zip(s,s[1:]))
        out.append(max(0, math.ceil(math.log2(max(L,1)/lmax))) if L>lmax else 0)
    return out
def split_seg(s, n):
    if n==0: return [s]
    a=s[0]; b=s[-1]
    if len(s)==2:
        m=Point((a.x+b.x)/2,(a.y+b.y)/2,'line'); return split_seg([a,m],n-1)+split_seg([m,b],n-1)
    c1=s[1]; l=Point((a.x+c1.x)/2,(a.y+c1.y)/2,None); r=Point((c1.x+b.x)/2,(c1.y+b.y)/2,None)
    m=Point((l.x+r.x)/2,(l.y+r.y)/2,'qcurve')
    return split_seg([a,l,m],n-1)+split_seg([m,r,b],n-1)
def apply_plan(c, pl, curvify=True):
    segs=segments(c); out=[]
    for s,n in zip(segs,pl):
        for ss in split_seg(s,n):
            if curvify and len(ss)==2:   # a line becomes a flat quad, so effects can bend it
                a,b=ss; ss=[a,Point((a.x+b.x)/2,(a.y+b.y)/2,None),b]
            out+=ss[:-1]
    for i,p in enumerate(out):
        if p.type: p.type='qcurve' if out[i-1].type is None else 'line'
    c.points.clear()
    for p in out: c.points.append(Point(p.x,p.y,p.type))
