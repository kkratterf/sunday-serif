"""Merge: the base contours of the current sources + the pores added by morepores.py.
usage: rebase.py MAIN_STYLEDIR PORES_STYLEDIR OUT_STYLEDIR"""
import sys, glob, os, ufoLib2, sim
main_dir, pore_dir, out_dir = sys.argv[1:4]
os.makedirs(out_dir, exist_ok=True)
REF = {}
for p in sorted(glob.glob(os.path.join(main_dir, '*.ufo'))):
    name = os.path.basename(p)
    M = ufoLib2.Font.open(p); P = ufoLib2.Font.open(os.path.join(pore_dir, name))
    pre = 'SundaySerif-Italic-' if '-Italic-' in name else 'SundaySerif-'
    ref = REF.setdefault(pre, ufoLib2.Font.open(os.path.join(main_dir, pre + 'Regular-B0.ufo')))
    for g in M:
        if g.name not in P: continue
        pg = P[g.name]
        # number of base contours = contours in main minus main's pores; pores sit at the end in both
        r = ufoLib2.Font  # noqa
        k = sim.outline_count(ref[g.name]) if g.name in ref else 0
        g.contours[k:] = [c for c in pg.contours[k:]]
    M.save(os.path.join(out_dir, name), overwrite=True)
print('ok')
