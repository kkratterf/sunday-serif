"""Render the README images into .github/readme/ with headless Chrome (after `make build`).

usage: python scripts/readme_images.py [--chrome PATH]

Needs Google Chrome (or Chromium) and Pillow: uv run --with pillow python scripts/readme_images.py
"""
import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".github" / "readme"
VF = (ROOT / "fonts" / "variable").as_uri()
CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser",
]
PAPER, INK, MUTED, LINE = "#F9F9F7", "#131313", "#6D6B67", "#E7E6E1"

HEAD = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: S; src: url("{VF}/SundaySerif%5BBURN,INKB,WORN,wght%5D.ttf"); font-weight: 400 600; }}
@font-face {{ font-family: S; src: url("{VF}/SundaySerif-Italic%5BBURN,INKB,WORN,wght%5D.ttf"); font-weight: 400 600; font-style: italic; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: {PAPER}; color: {INK}; overflow: hidden; }}
body {{ font-family: S; padding: 64px 80px; }}
.label {{ font: 500 22px/1 -apple-system, "Helvetica Neue", Arial, sans-serif; color: {MUTED}; letter-spacing: .02em; }}
.v {{ font-variation-settings: "BURN" var(--b, 0), "INKB" var(--i, 0), "WORN" var(--w, 0); }}
</style></head><body>"""


def page(body, width, height):
    return HEAD.replace("padding: 64px 80px;", f"padding: 64px 80px; width: {width}px; height: {height}px;") + body


def shoot(chrome, html, out, width, height, scale=2):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    subprocess.run([chrome, "--headless=new", "--hide-scrollbars", "--allow-file-access-from-files",
                    f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
                    "--virtual-time-budget=3000", f"--screenshot={out}", Path(f.name).as_uri()],
                   check=True, capture_output=True)


def banner(chrome, burn, ink, worn, out):
    w, h = 1280, 640
    body = f"""<div class="v" style="--b:{burn};--i:{ink};--w:{worn};height:100%;display:flex;flex-direction:column;justify-content:space-between">
<div style="font-size:200px;line-height:.92;letter-spacing:-.03em">Sunday<br><i>Serif</i></div>
<div class="label" style="display:flex;justify-content:space-between;font-size:26px">
<span>A soft serif for slow days</span><span>Light Burn {burn:+.0f} · Ink Bleed {ink:.0f} · Worn Print {worn:.0f}</span><span>Free &amp; open source</span></div></div>"""
    shoot(chrome, page(body, w, h), out, w, h)


def animated_banner(chrome):
    tmp = Path(tempfile.mkdtemp())
    keys = [(0, 0, 0), (-100, 0, 0), (0, 0, 0), (100, 0, 0), (0, 0, 0), (0, 100, 0), (0, 0, 0), (0, 0, 100), (0, 0, 0)]
    steps, n = 10, 0
    for (a, b) in zip(keys, keys[1:]):
        for s in range(steps):
            t = (1 - math.cos(math.pi * s / steps)) / 2
            v = [round(x + (y - x) * t) for x, y in zip(a, b)]
            banner(chrome, *v, tmp / f"f{n:03d}.png")
            n += 1
    from PIL import Image

    frames = [Image.open(tmp / f"f{i:03d}.png").convert("RGB").resize((1280, 640), Image.LANCZOS) for i in range(n)]
    # Hold the plain frames between effects a little longer.
    durations = [700 if i % steps == 0 else 70 for i in range(n)]
    frames[0].save(OUT / "banner.webp", save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, quality=80, method=6)
    shutil.copy(tmp / "f000.png", OUT / "banner.png")
    shutil.rmtree(tmp)


def weights(chrome):
    w, h = 1280, 560
    rows = "".join(
        f"""<div style="display:flex;align-items:baseline;justify-content:space-between;border-top:1px solid {LINE};padding:22px 0">
<span style="font-size:76px;font-weight:{wg}">Domenica, lentamente</span><span style="font-size:76px;font-weight:{wg};font-style:italic">&amp; con calma</span>
<span class="label">{name} {wg}</span></div>"""
        for wg, name in ((400, "Regular"), (500, "Medium"), (600, "SemiBold")))
    shoot(chrome, page(f'<div class="label" style="margin-bottom:24px">Weight · wght 400–600 · roman and italic</div>{rows}', w, h),
          OUT / "weights.png", w, h)


def axis(chrome, name, tag, var, values, file):
    w, h = 1280, 110 * len(values) + 140
    rows = "".join(
        f"""<div style="display:flex;align-items:center;border-top:1px solid {LINE};padding:6px 0">
<span class="label" style="width:120px">{v:+d}</span><span class="v" style="--{var}:{v};font-size:84px;line-height:1.15">Sunday afternoon</span></div>"""
        for v in values)
    shoot(chrome, page(f'<div class="label" style="margin-bottom:20px">{name} · {tag}</div>{rows}', w, h), OUT / file, w, h)


def glyphs(chrome):
    w, h = 1280, 760
    chars = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 "
             "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØŒÙÚÛÜÝÞß àáâãäåæçèéêëìíîïðñòóôõöøœùúûüýþÿ "
             "ĀăĄćČĎđĘěĞĪıĽŁŃŇŐŔŘŚŞŠŢŤŮŰŲŸŹŻŽ &@#%‰§¶†‡€£¥¢$ “”‘’«»‹›¡¿!?.,:;…–— ()[]{}/\\|*•·°©®™ ←↑→↓ +−×÷=<>~^")
    body = (f'<div class="label" style="margin-bottom:28px">Basic Latin · Latin-1 · Latin Extended-A</div>'
            f'<div style="font-size:58px;line-height:1.28;letter-spacing:.06em;word-break:break-all">{chars}</div>')
    shoot(chrome, page(body, w, h), OUT / "glyphs.png", w, h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome")
    args = ap.parse_args()
    chrome = args.chrome or next((c for c in CHROMES if shutil.which(c) or Path(c).exists()), None)
    if not chrome:
        raise SystemExit("Chrome or Chromium not found: pass --chrome PATH")
    OUT.mkdir(parents=True, exist_ok=True)
    weights(chrome)
    axis(chrome, "Light Burn", "BURN −100…100", "b", [-100, -50, 0, 50, 100], "light-burn.png")
    axis(chrome, "Ink Bleed", "INKB 0…100", "i", [0, 50, 100], "ink-bleed.png")
    axis(chrome, "Worn Print", "WORN 0…100", "w", [0, 50, 100], "worn-print.png")
    glyphs(chrome)
    animated_banner(chrome)
    print("written:", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
