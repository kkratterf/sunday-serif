"""Generators of the Ink Bleed (Ink100) and Worn Print (Worn100) masters.

These are the scripts that made the effect masters on main, kept as they ran (the only change:
they skip the Bold masters, which scripts/derive_weight.py rebuilds from Regular). They work on
one style folder at a time, on the drawn weight (Regular), and import each other, so run them
with scripts/effects as the working directory, from the .venv-fx virtualenv:

    uv venv --python 3.12 .venv-fx && uv pip install --python .venv-fx -r requirements-fx.txt
    cd scripts/effects

Pipeline, in order (ROOT = the repo root; same commands for Italic with SundaySerif-Italic-):

1. morepores.py STYLEDIR SundaySerif- 3.0e-6
   Worn Print pores in the style of the hand-drawn ones (thin tilted ellipses near the edges),
   appended after the base contours, open only in Worn100. Ran on a copy of sources/Roman.
2. rebase.py ROOT/sources/Roman PORES_STYLEDIR OUT_STYLEDIR
   The base contours of the sources plus the pores from step 1.
3. LMAX=110 inkroll.py OUT_STYLEDIR SundaySerif- [glyph ...]
   Densifies every master alike (dens.py), then redraws each Ink100 master glyph by glyph:
   ink simulation (blur + low-frequency noise + surface tension, sim2.ink_sim with the final
   parameters in sim2.IK) and the outline fitted onto it (sim2.fit_mono). Light Burn 0: counter
   0.5, strength 1.0. Light Burn 100: its Ink100 master equals the plain one. OUT_STYLEDIR then
   replaced sources/Roman.
4. grainpores.py ROOT/sources/Roman SundaySerif- [glyph ...]
   Worn Print grain, dust and starved patches: 4-point all-off-curve holes appended after the
   pores, open only in Worn100. N = min(300, area / stem^2 * 26); share edge .55, patch .3,
   dust .15. Set DENS (default 1.0) to scale the count.

Then run scripts/derive_weight.py Bold 700 and `make variable`.

Every step appends or densifies, so none of them can run twice on the same glyph: rerunning
inkroll.py densifies again, rerunning grainpores.py stacks a second grain. Use them on glyphs
that do not have the effect yet (a new glyph, or a redrawn one reset to its plain outline),
passing the glyph names. Seeds come from the glyph name, so results are reproducible.

Helpers: sim.py (raster, noise, pore shapes), sim2.py (ink simulation and outline fit; the
worn "scratch" and "needle" code in it is an unused earlier attempt), dens.py (densify),
flat.py (contour sampling), effects_v1.py (the first offset-based version, superseded; sim2
still uses its geometry helpers).
"""
